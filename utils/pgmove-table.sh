#!/usr/bin/env bash
set -euo pipefail

# pgmove-table.sh
#
# Copie une table Postgres depuis une base source vers une base cible, en
# conservant les objets de structure utiles au transfert : index, séquences,
# contraintes et éventuellement triggers selon l'option --no-triggers.
#
# Objectif principal : déplacer des données sans reconstruire la table à la main
# depuis le SQL, en utilisant pg_dump custom + pg_restore.
#
# Pré-requis :
#   - PostgreSQL client tools installés : psql, pg_dump, pg_restore
#   - Accès réseau/credentials vers les deux bases
#   - Le schéma cible doit déjà exister
#   - Si la table source contient des colonnes PostGIS, la cible doit avoir
#     l'extension postgis installée
#
# Contraintes connues :
#   - Les permissions, propriétaires et rôles ne sont pas transférés
#     (--no-owner --no-privileges)
#   - Le script ne copie pas les données "à chaud" ; il fait un dump complet de
#     la table puis une restauration sur la cible
#   - Les triggers peuvent être ignorés avec --no-triggers, ce qui évite de
#     copier les déclencheurs si le besoin est purement de données/structure
#
# Exemple d'utilisation :
#   ./utils/pgmove-table.sh \
#     --src "service=prod" \
#     --src-table "public.my_table" \
#     --dst "uri=postgresql://user:pass@host:5432/db_target" \
#     --dst-schema "public" \
#     --dst-table "my_table_copy" \
#     --jobs 8 --verbose
#
# Exemple avec migration vers un schéma différent :
#   ./utils/pgmove-table.sh \
#     --src "service=prod" \
#     --src-table "public.my_table" \
#     --dst "service=staging" \
#     --dst-schema "staging" \
#     --no-triggers \
#     --force-drop
#
# Remarques de sécurité :
#   - Si la table cible existe, le script demande confirmation sauf avec
#     --force-drop
#   - Le dump est conservé dans le répertoire de travail pour inspection ou
#     reprise manuelle
#
# ---- Defaults ----
JOBS="${JOBS:-4}"
NO_TRIGGERS="false"
FORCE_DROP="false"
WORKDIR="${WORKDIR:-/tmp}"
DUMPFILE=""
VERBOSE="${VERBOSE:-false}"

usage() {
  cat <<'EOF'
Description:
  Déplace une table PostgreSQL d'une source vers une cible, en conservant la
  structure principale (index, séquences, contraintes), sans copier les
  permissions/owners.

Usage:
  pgmove-table.sh \
    --src "service=srcsvc|uri=postgres://..." \
    --src-table "schema.table" \
    --dst "service=dstsvc|uri=postgres://..." \
    --dst-schema "schema" \
    [--dst-table "new_table_name"] \
    [--jobs N] [--no-triggers] [--force-drop] [--workdir /path/tmp] [--verbose]

Options:
  --src             Connexion source: "service=NAME" (PGSERVICE) ou "uri=postgres://..."
  --src-table       Table source au format "schema.table"
  --dst             Connexion cible: "service=NAME" (PGSERVICE) ou "uri=postgres://..."
  --dst-schema      Schéma cible (doit exister)
  --dst-table       Nom de table cible (sinon = nom source)
  --jobs            Parallélisme pg_restore (défaut: 4)
  --no-triggers     N'exporte pas les triggers (index et séquences conservés)
  --force-drop      Si la table cible existe, la DROP sans demander
  --workdir         Répertoire pour le dump list et le fichier .dump (défaut: /tmp)
  --verbose         Affiche plus de logs détaillés
  -h, --help        Affiche cette aide

Comportement:
  - Dump de la table source au format custom via pg_dump
  - Restauration sur la base cible avec --clean pour éliminer les objets existants
  - Si la table source contient geometry/geography, validation de l'extension PostGIS
  - Ajustement des séquences via setval afin de conserver l'ordre de génération
  - Si le schéma de destination est différent, la table est déplacée via ALTER TABLE ... SET SCHEMA
  - Si --dst-table est différent, le nom est ajusté après restauration

Notes:
  - Les rôles/privileges ne sont pas transférés (--no-owner --no-privileges).
  - Les séquences et index sont transférés, puis réalignés.
  - PostGIS: si la table source contient geometry/geography, vérifie que postgis est bien installé en cible.
  - Le dump est laissé sur disque dans le workdir pour diagnostic ou reprise manuelle.
EOF
}

log() { echo "[$(date +'%F %T')] $*"; }
vlog() { if [[ "$VERBOSE" == "true" ]]; then echo "[$(date +'%F %T')] $*"; fi; }

# ---- Parse args ----
SRC_CONN=""
DST_CONN=""
SRC_TABLE=""
SRC_SCHEMA=""
DST_SCHEMA=""
DST_TABLE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --src)         SRC_CONN="$2"; shift 2;;
    --dst)         DST_CONN="$2"; shift 2;;
    --src-table)   SRC_TABLE="$2"; shift 2;;
    --dst-schema)  DST_SCHEMA="$2"; shift 2;;
    --dst-table)   DST_TABLE="$2"; shift 2;;
    --jobs)        JOBS="$2"; shift 2;;
    --no-triggers) NO_TRIGGERS="true"; shift;;
    --force-drop)  FORCE_DROP="true"; shift;;
    --workdir)     WORKDIR="$2"; shift 2;;
    --verbose)     VERBOSE="true"; shift;;
    -h|--help)     usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

# ---- Validate ----
[[ -z "$SRC_CONN" || -z "$DST_CONN" || -z "$SRC_TABLE" || -z "$DST_SCHEMA" ]] && { usage; exit 1; }
if [[ "$SRC_TABLE" != *.* ]]; then echo "ERR: --src-table doit être 'schema.table'"; exit 1; fi
SRC_SCHEMA="${SRC_TABLE%%.*}"
SRC_TNAME="${SRC_TABLE##*.}"
DST_TABLE="${DST_TABLE:-$SRC_TNAME}"

mkdir -p "$WORKDIR"

# ---- Build env + psql wrappers ----
conn_env() {
  local side="$1" conn="$2"
  if [[ "$conn" == service=* ]]; then
    echo "PGSERVICE=${conn#service=}"
  elif [[ "$conn" == uri=* || "$conn" == postgres://* || "$conn" == postgresql://* ]]; then
    echo "PGCONNECT_TIMEOUT=10 PGOPTIONS= ${side}_URI='$conn'"
  else
    echo "ERR"; return 1
  fi
}

# Validation précoce des formats de connexion
conn_env SRC "$SRC_CONN" >/dev/null || { echo "Connexion source invalide"; exit 1; }
conn_env DST "$DST_CONN" >/dev/null || { echo "Connexion cible invalide"; exit 1; }

# helper: run psql on source/dest
psql_src() {
  if [[ "$SRC_CONN" == service=* ]]; then
    PGSERVICE="${SRC_CONN#service=}" psql -X -v ON_ERROR_STOP=1 -Atc "$1"
  else
    psql "${SRC_CONN#uri=}" -X -v ON_ERROR_STOP=1 -Atc "$1"
  fi
}
psql_dst() {
  if [[ "$DST_CONN" == service=* ]]; then
    PGSERVICE="${DST_CONN#service=}" psql -X -v ON_ERROR_STOP=1 -Atc "$1"
  else
    psql "${DST_CONN#uri=}" -X -v ON_ERROR_STOP=1 -Atc "$1"
  fi
}

# helper: run pg_dump / pg_restore with right target
run_pg_dump() {
  if [[ "$SRC_CONN" == service=* ]]; then
    PGSERVICE="${SRC_CONN#service=}" pg_dump "$@"
  else
    pg_dump "${SRC_CONN#uri=}" "$@"
  fi
}
run_pg_restore() {
  if [[ "$DST_CONN" == service=* ]]; then
    PGSERVICE="${DST_CONN#service=}" pg_restore "$@"
  else
    pg_restore "${DST_CONN#uri=}" "$@"
  fi
}

# ---- Connectivity checks ----
log "Vérification connexions…"
vlog "Source: $SRC_CONN ; Cible: $DST_CONN"
psql_src "SELECT current_database() || ' @ ' || version();" >/dev/null
psql_dst "SELECT current_database() || ' @ ' || version();" >/dev/null

# ---- Existence checks & PostGIS ----
log "Vérification existence table source ${SRC_SCHEMA}.${SRC_TNAME}…"
SRC_EXISTS=$(psql_src "SELECT to_regclass('${SRC_SCHEMA}.${SRC_TNAME}') IS NOT NULL;")
[[ "$SRC_EXISTS" != "t" ]] && { echo "ERR: table source introuvable"; exit 1; }

log "Vérification schéma cible ${DST_SCHEMA}…"
DST_SCHEMA_EXISTS=$(psql_dst "SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname='${DST_SCHEMA}');")
[[ "$DST_SCHEMA_EXISTS" != "t" ]] && { echo "ERR: schéma cible inexistant"; exit 1; }

DST_DB=$(psql_dst "SELECT current_database();")
[[ -z "$DST_DB" ]] && { echo "ERR: base cible introuvable"; exit 1; }

DST_FULL="${DST_SCHEMA}.${DST_TABLE}"
DST_EXISTS=$(psql_dst "SELECT to_regclass('${DST_FULL}') IS NOT NULL;")
if [[ "$DST_EXISTS" == "t" ]]; then
  if [[ "$FORCE_DROP" == "true" ]]; then
    log "DROP de la table cible existante ${DST_FULL} (--force-drop)."
    psql_dst "DROP TABLE ${DST_FULL} CASCADE;"
  else
    echo "La table cible ${DST_FULL} existe déjà."
    read -rp "Voulez-vous la DROP ? (yes/no) " ans
    if [[ "$ans" == "yes" ]]; then
      psql_dst "DROP TABLE ${DST_FULL} CASCADE;"
    else
      echo "Abandon."
      exit 1
    fi
  fi
fi

# Source has geometry/geography columns?
HAS_GEO=$(psql_src "
SELECT EXISTS(
  SELECT 1 FROM information_schema.columns
  WHERE table_schema='${SRC_SCHEMA}' AND table_name='${SRC_TNAME}'
    AND udt_name IN ('geometry','geography')
);
")
if [[ "$HAS_GEO" == "t" ]]; then
  log "La table source contient des colonnes géo; vérification PostGIS côté cible…"
  HAS_POSTGIS=$(psql_dst "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='postgis');")
  if [[ "$HAS_POSTGIS" != "t" ]]; then
    echo "ERR: PostGIS n'est pas installé en cible, mais requis."
    echo "Installe en cible:  CREATE EXTENSION postgis;"
    exit 1
  fi
fi

# ---- Dump ----
DUMPFILE="${WORKDIR}/pgmove_${SRC_SCHEMA}_${SRC_TNAME}_$(date +%s).dump"
log "Dump de la table source (format custom)…"
run_pg_dump \
  --format=custom \
  --no-owner --no-privileges \
  --table="${SRC_SCHEMA}.${SRC_TNAME}" \
  --file="${DUMPFILE}"

# Optionnel: filtrer les TRIGGER via TOC list (portable macOS/Linux)
LISTFILE="${DUMPFILE}.list"
if [[ "$NO_TRIGGERS" == "true" ]]; then
  log "Exclusion des TRIGGER (pg_restore -l/-L)…"
  run_pg_restore -l "${DUMPFILE}" > "${LISTFILE}"
  # Retirer les lignes contenant ' TRIGGER ' (évite faux positifs)
  awk '!/ TRIGGER([[:space:]]|$)/' "${LISTFILE}" > "${LISTFILE}.filtered"
  mv "${LISTFILE}.filtered" "${LISTFILE}"
fi

# Fonction de restauration avec compatibilité transaction_timeout
restore_with_compat() {
  local with_list="$1"
  local rc=0
  # Ajout --schema et --clean pour forcer le schéma cible et supprimer la table existante
  if [[ "$with_list" == "true" ]]; then
    if ! run_pg_restore --dbname="${DST_DB}" --no-owner --no-privileges --disable-triggers --clean -j "${JOBS}" -L "${LISTFILE}" "${DUMPFILE}" 2>"${DUMPFILE}.stderr"; then
      if grep -q 'unrecognized configuration parameter "transaction_timeout"' "${DUMPFILE}.stderr"; then
        log "Compat: serveur ne connaît pas transaction_timeout → génération SQL filtrée…"
        run_pg_restore --no-owner --no-privileges --disable-triggers --clean -L "${LISTFILE}" "${DUMPFILE}" -f - \
        | awk '!/^SET[[:space:]]+transaction_timeout[[:space:]]*=/' \
        | ( if [[ "$DST_CONN" == service=* ]]; then PGSERVICE="${DST_CONN#service=}" psql -X -v ON_ERROR_STOP=1 --dbname="${DST_DB}"; else psql "${DST_CONN#uri=}" -X -v ON_ERROR_STOP=1 --dbname="${DST_DB}"; fi )
      else rc=1; fi
    fi
  else
    if ! run_pg_restore --dbname="${DST_DB}" --no-owner --no-privileges --disable-triggers --clean -j "${JOBS}" "${DUMPFILE}" 2>"${DUMPFILE}.stderr"; then
      if grep -q 'unrecognized configuration parameter "transaction_timeout"' "${DUMPFILE}.stderr"; then
        log "Compat: serveur ne connaît pas transaction_timeout → génération SQL filtrée…"
        run_pg_restore --no-owner --no-privileges --disable-triggers --clean "${DUMPFILE}" -f - \
        | awk '!/^SET[[:space:]]+transaction_timeout[[:space:]]*=/' \
        | ( if [[ "$DST_CONN" == service=* ]]; then PGSERVICE="${DST_CONN#service=}" psql -X -v ON_ERROR_STOP=1 --dbname="${DST_DB}"; else psql "${DST_CONN#uri=}" -X -v ON_ERROR_STOP=1 --dbname="${DST_DB}"; fi )
      else rc=1; fi
    fi
  fi
  return $rc
}

# ---- Restore (dans le schéma source), avec fallback compat ----
log "Restauration sur base ${DST_DB} (parallèle: ${JOBS})…"
if [[ "$NO_TRIGGERS" == "true" ]]; then
  restore_with_compat "true"
else
  restore_with_compat "false"
fi

## Rétablissement du déplacement de schéma après restauration
if [[ "${DST_SCHEMA}" != "${SRC_SCHEMA}" ]]; then
  log "Déplacement ${SRC_SCHEMA}.${SRC_TNAME} -> schéma ${DST_SCHEMA}…"
  EXISTS_POST=$(psql_dst "SELECT to_regclass('${SRC_SCHEMA}.${SRC_TNAME}') IS NOT NULL;")
  [[ "$EXISTS_POST" != "t" ]] && { echo "ERR: table restaurée introuvable pour SET SCHEMA"; exit 1; }
  psql_dst "ALTER TABLE ${SRC_SCHEMA}.${SRC_TNAME} SET SCHEMA ${DST_SCHEMA};"
fi
if [[ "$DST_TABLE" != "$SRC_TNAME" ]]; then
  log "Renommage ${DST_SCHEMA}.${SRC_TNAME} -> ${DST_FULL}…"
  psql_dst "ALTER TABLE ${DST_SCHEMA}.${SRC_TNAME} RENAME TO ${DST_TABLE};"
fi

# ---- Ajustement des sequences (par sécurité) ----
# Pour chaque colonne avec default nextval(...), on réaligne le setval
log "Ajustement des séquences associées (setval)…"
DO_BLOCK="DO \$\$
DECLARE r record; seq_name text; maxval bigint;
BEGIN
  FOR r IN
    SELECT a.attrelid::regclass AS tbl, a.attname AS col,
           regexp_replace(pg_get_expr(ad.adbin, ad.adrelid), '.*nextval\\(''([^'']+)''::regclass\\).*', '\\1') AS seq
    FROM pg_attribute a
    JOIN pg_class c ON c.oid=a.attrelid
    JOIN pg_namespace n ON n.oid=c.relnamespace
    JOIN pg_attrdef ad ON ad.adrelid=a.attrelid AND ad.adnum=a.attnum
    WHERE n.nspname='${DST_SCHEMA}' AND c.relname='${DST_TABLE}'
      AND pg_get_expr(ad.adbin, ad.adrelid) LIKE 'nextval(%'
  LOOP
    EXECUTE format('SELECT COALESCE(MAX(%I),0) FROM %s', r.col, r.tbl) INTO maxval;
    EXECUTE format('SELECT setval(%L, GREATEST(%s,1), true)', r.seq, maxval);
  END LOOP;
END
\$\$;"
psql_dst "$DO_BLOCK"

# ---- Recap ----
ROWS=$(psql_dst "SELECT COUNT(*) FROM ${DST_FULL};")
SIZE=$(psql_dst "SELECT pg_size_pretty(pg_total_relation_size('${DST_FULL}'));")
log "Terminé. ${DST_FULL}: ${ROWS} lignes, taille ${SIZE}"
log "Dump conservé: ${DUMPFILE}"

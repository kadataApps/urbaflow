# UrbaFlow

ETL de traitement des données liées à l'urbanisme :

- MAJIC
- DVF (données Valeurs Foncières)
- DGFiP TOPO
- FFPM (Fichiers Fonciers Personnes Morales)
- Cadastre
- Bati
- PLU
- Géosirene

L'ETL est composé de scripts python et de fichiers SQL.
Il a été testé pour les environnements linux et OSX.

UrbaFlow vient avec quelques utilitaires pour faciliter la gestion des bases de données PostgreSQL/PostGIS.

Le script `utils/pgmove-table.sh` permet de copier une table d'une base source vers une base cible tout en conservant les éléments essentiels de structure : index, séquences, contraintes et, selon le cas, les triggers. Il est utile pour migrer une table sans recréer manuellement les objets dépendants ni réécrire le schéma.

## Prérequis

- PostgreSQL client tools (`psql`, `pg_dump`, `pg_restore`) installés sur la machine ou dans l'environnement d'exécution.
- Accès réseau et identifiants valides sur les bases source et cible.
- Un schéma de destination existant.
- Si la table source contient des colonnes géographiques PostGIS, la base cible doit avoir l'extension `postgis` activée.
- Docker : permet de lancer les scripts dans un environnement maitrisé avec les bonnes dépendances.
  - (installation sur windows: [https://docs.docker.com/desktop/install/windows-install/])
  - (installation sur mac: [https://docs.docker.com/desktop/install/mac-install/])
  - (installation sur linux: [https://docs.docker.com/engine/install/])
- (optionnel) Make (installation sur windows: [https://chocolatey.org/packages/make])

Pour le développement local, installer [uv](https://docs.astral.sh/uv/).

```shell
cd urbaflow
uv sync
```

Les commandes locales s'exécutent avec `uv run`, par exemple `uv run ruff check`.

### Utiliser un PGSERVICE

Le script accepte deux types de connexion :

- un `PGSERVICE` sous la forme `service=nom_du_service`
- ou une URI PostgreSQL sous la forme `uri=postgresql://utilisateur:motdepasse@hote:5432/base`

Pour utiliser un `PGSERVICE`, il faut définir un service dans le fichier `~/.pg_service.conf` avec une section du type :

```ini
[srcsvc]
host=prod-db.internal
port=5432
dbname=source_db
user=app_user
password=secret
sslmode=require
```

Ensuite, on appelle le script avec :

```bash
./utils/pgmove-table.sh \
  --src "service=srcsvc" \
  --src-table "public.my_table" \
  --dst "service=dstsvc" \
  --dst-schema "public" \
  --verbose
```

Autre exemple, avec une connexion directe par URI :

```bash
./utils/pgmove-table.sh \
  --src "uri=postgresql://user:pass@host:5432/source_db" \
  --src-table "public.my_table" \
  --dst "uri=postgresql://user:pass@host:5432/target_db" \
  --dst-schema "public"
```

## Principe

Les fichiers SQL sont copiés, puis certaines parties de ces fichiers sont remplacées/réécrites (changement de "variables", notamment les dates, schémas...) avant d'être exécutées.

L'ETL est exécuté dans une image Docker afin d'utiliser un environnement maîtrisé, incluant notamment GEOS et GDAL. Les dépendances Python sont installées dans l'image avec `uv` à partir de `urbaflow/pyproject.toml` et `urbaflow/uv.lock`.

Les scripts sont lancés via une ligne de commande depuis un container docker.

Les données sources sont montées dans un volume attaché au container dans le répertoire `/data`.

L'ETL charge les données dans une base PostGIS qui doit être configurée dans les variables d'environnement.

## Documentation

### GeoSIRENE

[Base SIRENE des établissements (SIRET) - géolocalisée avec la Base d'Adresse Nationale (BAN)](https://www.data.gouv.fr/fr/datasets/base-sirene-des-etablissements-siret-geolocalisee-avec-la-base-dadresse-nationale-ban/)

Jeu de données: <https://files.data.gouv.fr/geo-sirene/last/dep/>

### LOCOMVAC

[documentation LOCOMVAC sur le site collectivites-locales.gouv.fr](https://www.collectivites-locales.gouv.fr/sites/default/files/migration/fiche_technique_locaux_vacants_commerciaux_2020.pdf)

## Exécuter l'ETL avec Docker

Les commandes d'import sont exécutées dans le conteneur `urbaflow`. Les données définies par `PATH_TO_DATA` sont disponibles dans le conteneur sous `/data`.

1. Créer le fichier `.env` à la racine du projet à partir de `.env.example`, puis renseigner les variables suivantes :
    - le chemin des fichiers majic à charger avec la variable `PATH_TO_DATA`. Le
      chemin sera monté dans le conteneur sur `/data/`.
    - Configuration de la base de données :
      - Si besoin d'une base postgis à la volée, lancer la base PostGIS avec Docker `make start-postgis` (cette base est
      exposée sur le port 5432).
      - si la base de données est lancée avec docker-compose, conserver `POSTGRES_HOST=postgis`
      - si la base de données n'est pas lancée avec le même docker compose, utiliser `POSTGRES_HOST=host.docker.internal` pour rediriger vers le host de l'hôte (la machine qui exécute le container)
      - Configurer également : `POSTGRES_USER`, `POSTGRES_PASS`, `POSTGRES_DB`, `POSTGRES_PORT` (les mêmes variables sont utilisées pour le lancement de la base de données avec docker-compose et pour le lancement de l'image de processing)
      - Configurer également : `IMPORT_SCHEMA` (schéma de la base de données dans lequel les données seront importées)
2. Construire l'image :

```shell
make build-urbaflow
```

3. Lancer la commmande d'import souhaitée :

- MAJIC: cf. [MAJIC.md](MAJIC.md)
- DGFIP TOPO: cf. [DGFiP_TOPO.md](DGFiP_TOPO.md)

4. Pour ouvrir un shell de diagnostic dans l'image :

```shell
make urbaflow
```

## Commandes disponibles (CLI `main.py`)

Le point d'entrée CLI est `urbaflow/main.py` (Typer).

### Lancement de la CLI

- Avec Docker :

```shell
docker compose run --rm urbaflow python urbaflow/main.py --help
```

- En local (développement) :

```shell
uv run python urbaflow/main.py --help
```

### Commandes

- `dvf <departements> [dirname]`
  - Importe les données DVF pour un ou plusieurs départements.
  - `dirname` est optionnel (par défaut: `/data/`).

- `dgfip-topo [dirname]`
  - Importe les entités topographiques DGFiP.
  - `dirname` est optionnel (par défaut: `/data/`).

- `locomvac [dirname]`
  - Importe les fichiers LOCOMVAC.
  - `dirname` est optionnel (par défaut: `/data/`).

- `lovac [dirname]`
  - Importe les fichiers LOVAC.
  - `dirname` est optionnel (par défaut: `/data/`).

- `lovac-fil [dirname] [OPTIONS]`
  - Importe les données LOVAC FIL.
  - Options :
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `lovac_fil`)
    - `--recursive / --no-recursive` (défaut: `--no-recursive`)
    - `--recreate / --no-recreate` (défaut: `--recreate`)

- `majic [dirname] [steps...]`
  - Importe MAJIC/Cadastre.
  - `steps` permet de limiter l'exécution à certaines étapes.

- `risques-cavite [dirname] [OPTIONS]`
  - Importe les données de risques de cavités.
  - Fournir soit `dirname`, soit `--department`.
  - Options :
    - `-d, --department TEXT`
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `risques_cavite`)
    - `--recreate / --no-recreate` (défaut: `--recreate`)

- `risques-rga [dirname] [OPTIONS]`
  - Importe les données de retrait-gonflement des argiles.
  - Fournir soit `dirname`, soit `--departement`.
  - Options :
    - `-d, --departement TEXT`
    - `--schema TEXT` (défaut: `public`)
    - `--recreate / --no-recreate` (défaut: `--no-recreate`)

- `risques-remnappes [dirname] [OPTIONS]`
  - Importe les données de risques d'inondation par remontée de nappe (REMNAPPES).
  - Fournir soit `dirname`, soit `--departement`.
  - Options :
    - `-d, --departement TEXT`
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `risques_remnappes`)
    - `--recreate / --no-recreate` (défaut: `--no-recreate`)

- `risques-mvt [dirname] [OPTIONS]`
  - Importe les données de mouvements de terrain (MVT).
  - Fournir soit `dirname`, soit `--departement`.
  - Options :
    - `-d, --departement TEXT`
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `risques_mvt`)
    - `--recreate / --no-recreate` (défaut: `--no-recreate`)

- `risques-casias [dirname] [OPTIONS]`
  - Importe les données de carte des anciens sites industriels et activités de service (CASIAS).
  - Fournir soit `dirname`, soit `--departement`.
  - Options :
    - `-d, --departement TEXT`
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `risques_casias`)
    - `--recreate / --no-recreate` (défaut: `--no-recreate`)

- `risques-sis [dirname] [OPTIONS]`
  - Importe les secteurs d'information sur les sols (SIS). Cf. [INFOSOLS_SIS_SUP.md](INFOSOLS_SIS_SUP.md).
  - Fournir soit `dirname`, soit `--departement`.
  - Options :
    - `-d, --departement TEXT`
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `risques_sis`)
    - `--recreate / --no-recreate` (défaut: `--no-recreate`)

- `risques-sup [dirname] [OPTIONS]`
  - Importe les servitudes d'utilité publique (SUP). Cf. [INFOSOLS_SIS_SUP.md](INFOSOLS_SIS_SUP.md).
  - Fournir soit `dirname`, soit `--departement`.
  - Options :
    - `-d, --departement TEXT`
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `risques_sup`)
    - `--recreate / --no-recreate` (défaut: `--no-recreate`)

- `risques-tri [dirname] [OPTIONS]`
  - Importe les territoires à risques important d'inondation (TRI 2020).
  - Fournir soit `dirname`, soit `--departement`.
  - Options :
    - `-d, --departement TEXT`
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `risques_tri`)
    - `--recreate / --no-recreate` (défaut: `--no-recreate`)

- `risques-icpe [dirname] [OPTIONS]`
  - Importe la base nationale des installations classées pour la protection de l'environnement (ICPE).
  - `dirname` est optionnel (télécharge la base nationale WFS par défaut).
  - Options :
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `risques_icpe`)
    - `--recreate / --no-recreate` (défaut: `--no-recreate`)

- `risques-irep [dirname] [OPTIONS]`
  - Importe le registre national des émissions polluantes (IREP) consolidé par établissement.
  - `dirname` est optionnel (télécharge l'archive annuelle nationale par défaut).
  - Options :
    - `--year INTEGER` (défaut: `2024`)
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `risques_irep`)
    - `--recreate / --no-recreate` (défaut: `--no-recreate`)

- `risques-gaspar [dirname] [OPTIONS]`
  - Importe les procédures administratives relatives aux risques (GASPAR consolidé).
  - `dirname` est optionnel (télécharge l'archive nationale par défaut).
  - Options :
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `risques_gaspar`)
    - `--recreate / --no-recreate` (défaut: `--no-recreate`)

- `gpu-sup [dirname] [OPTIONS]`
  - Importe les servitudes d'utilité publique (SUP) du Géoportail de l'Urbanisme (fichiers GeoPackage d'extraction nationale).
  - `dirname` est optionnel (télécharge les fichiers GPKG depuis l'API Géoportail `download-latest` par défaut).
  - Les tables créées dans PostGIS sont préfixées par `gp_` (`gp_acte_sup`, `gp_assiette_sup_l`, `gp_assiette_sup_p`, `gp_assiette_sup_s`, `gp_generateur_sup_l`, `gp_generateur_sup_p`, `gp_generateur_sup_s`, `gp_gestionnaire_sup`, `gp_servitude`, `gp_servitude_acte_sup`).
  - Options :
    - `--schema TEXT` (défaut: `public`)
    - `--recreate / --no-recreate` (défaut: `--recreate`)

- `banatic-communes [dirname] [OPTIONS]`
  - Importe la table consolidée des communes BANATIC avec leur raccordement aux EPCI à fiscalité propre (EPCI FP).
  - `dirname` est optionnel (télécharge automatiquement les fichiers CSV depuis data.gouv.fr par défaut).
  - Options :
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `banatic_communes`)
    - `--recreate / --no-recreate` (défaut: `--recreate`)

- `epci-gpu <siren> [OPTIONS]`
  - Intégration des communes et des documents d'urbanisme / servitudes d'un EPCI à partir de son numéro SIREN.
  - Crée la table `banatic_communes_<SIREN>` enrichie par l'API APICARTO IGN (`is_rnu`, `is_coastline`).
  - Met à jour les 8 tables PostGIS `gpu_*` (`gpu_zone_urba`, `gpu_secteur_cc`, `gpu_prescription_surf`, `gpu_prescription_lin`, `gpu_prescription_pct`, `gpu_info_surf`, `gpu_info_lin`, `gpu_info_pct`) pour les partitions `DU_<insee>`, `PSMV_<insee>`, `DU_<siren>` et `PSMV_<siren>`.
  - Options :
    - `--schema TEXT` (défaut: `public`)
    - `--banatic-table TEXT` (défaut: `banatic_communes`)

- `gpu-plu [OPTIONS]`
  - Télécharge et importe les données géographiques PLU du Géoportail de l'Urbanisme via APICARTO.
  - Le périmètre est défini par **une seule** des options `--epci` ou `--commune`.
  - Un EPCI inclut ses partitions intercommunales et les partitions de toutes ses communes, résolues via `geo.api.gouv.fr`.
  - Importe les tables `urba_zone_urba`, `urba_prescription_surf`, `urba_prescription_lin`, `urba_prescription_pct` et `urba_info_surf`.
  - Les partitions du périmètre sont remplacées sans supprimer les données des autres territoires.
  - Les réponses GeoJSON sont conservées par défaut dans `urbaflow/temp/geoportail/plu/<code>/`.
  - Options :
    - `-e, --epci TEXT` (code SIREN de l'EPCI)
    - `-c, --commune TEXT` (code INSEE de la commune)
    - `--schema TEXT` (défaut: `public`)
    - `--download-dir PATH` (répertoire de téléchargement personnalisé)
    - `--keep-files / --no-keep-files` (défaut: `--keep-files`)

- `bdtopo-batiment [OPTIONS]`
  - Télécharge et importe les bâtiments de la BD TOPO® de l'IGN dans la table `bdtopo_batiment`.
  - Les archives départementales GeoPackage sont téléchargées depuis la Géoplateforme (`data.geopf.fr`), puis seule la couche `batiment` est importée (géométries `MultiPolygon` en Lambert 93).
  - Le périmètre est défini par **une seule** des options `--departement`, `--epci` ou `--communes` :
    - `--departement` : un ou plusieurs départements entiers ;
    - `--epci` : toutes les communes de l'EPCI, résolues via l'API Découpage administratif (`geo.api.gouv.fr`) ;
    - `--communes` : une liste de codes INSEE.
  - Chaque bâtiment est rattaché à une commune (et donc à un département) par jointure spatiale sur son point représentatif, ce qui alimente les colonnes `code_insee` et `code_departement`.
  - **L'import remplace les données existantes sur le périmètre** : suppression préalable des bâtiments de même `code_departement` (import départemental) ou des bâtiments des communes effectivement chargées (import par EPCI ou par communes). Les données hors périmètre ne sont pas touchées, et une commune demandée mais absente de la BD TOPO conserve ses données précédentes.
  - La colonne `millesime` conserve la date d'édition de la BD TOPO importée.
  - Chaque département téléchargé représente une archive de plusieurs centaines de Mo et un GeoPackage de plusieurs Go : prévoir l'espace disque correspondant dans `urbaflow/temp/`. Les fichiers sont supprimés après l'import, sauf avec `--keep-files`.
  - Options :
    - `-d, --departement TEXT` (codes séparés par des virgules, ex: `35` ou `35,22`)
    - `-e, --epci TEXT` (numéro SIREN de l'EPCI)
    - `-c, --communes TEXT` (codes INSEE séparés par des virgules)
    - `--millesime TEXT` (défaut: dernière édition disponible, ex: `2026-06-15`)
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `bdtopo_batiment`)
    - `--recreate / --no-recreate` (défaut: `--no-recreate`)
    - `--keep-files / --no-keep-files` (défaut: `--no-keep-files`, conserve l'archive et le GeoPackage téléchargés)

- `ocsge [OPTIONS]`
  - Télécharge et importe les données OCS GE (Occupation du Sol à Grande Échelle) de l'IGN dans les tables `ocsge_occupation_sol` et `ocsge_zone_construite`.
  - Les archives départementales GeoPackage sont téléchargées depuis la Géoplateforme (`data.geopf.fr`) ; les livraisons différentielles (`_DIFF`) sont ignorées au profit de la dernière édition complète.
  - Le périmètre est défini par **une seule** des options `--departement`, `--epci` ou `--communes` (mêmes règles de résolution que `bdtopo-batiment`).
  - OCS GE ne fournit pas de couche commune : seule la colonne `code_departement` est renseignée (pas de `code_insee`). Pour un périmètre EPCI ou communes, seuls les polygones intersectant les contours communaux (récupérés via l'API Découpage administratif) sont conservés.
  - **L'import remplace les données existantes sur le périmètre** : suppression préalable des enregistrements de même `code_departement` (import départemental) ou intersectant les contours des communes effectivement chargées (import par EPCI ou par communes). Les données hors périmètre ne sont pas touchées.
  - La colonne `millesime` conserve la date d'édition de l'OCS GE importée.
  - Le CRS source varie selon le territoire (Lambert-93 en métropole, CRS locaux outre-mer) ; les géométries sont systématiquement reprojetées en Lambert-93 (EPSG:2154) dans les tables cibles.
  - Chaque département téléchargé représente une archive de quelques dizaines à centaines de Mo : prévoir l'espace disque correspondant dans `urbaflow/temp/`. Les fichiers sont supprimés après l'import, sauf avec `--keep-files`.
  - Options :
    - `-d, --departement TEXT` (codes séparés par des virgules, ex: `35` ou `35,22`)
    - `-e, --epci TEXT` (numéro SIREN de l'EPCI)
    - `-c, --communes TEXT` (codes INSEE séparés par des virgules)
    - `--millesime TEXT` (défaut: dernière édition complète disponible, ex: `2023-01-01`)
    - `--schema TEXT` (défaut: `public`)
    - `--occupation-sol-table TEXT` (défaut: `ocsge_occupation_sol`)
    - `--zone-construite-table TEXT` (défaut: `ocsge_zone_construite`)
    - `--recreate / --no-recreate` (défaut: `--no-recreate`)
    - `--keep-files / --no-keep-files` (défaut: `--no-keep-files`, conserve l'archive et les GeoPackages téléchargés)

- `bpe [dirname] [OPTIONS]`
  - Importe la Base Permanente des Équipements (BPE / INSEE) géolocalisée.
  - `dirname` est optionnel (télécharge le fichier ZIP national BPE depuis l'INSEE par défaut).
  - Options :
    - `-d, --departement TEXT` (optionnel : limite l'import au département spécifié)
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `insee_bpe`)
    - `--recreate / --no-recreate` (défaut: `--recreate`)

- `mh [dirname] [OPTIONS]`
  - Importe les immeubles protégés au titre des Monuments Historiques (MH).
  - `dirname` est optionnel (télécharge le fichier GeoJSON national depuis data.gouv.fr par défaut).
  - Options :
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `patrimoine_immeubles_proteges_mh`)
    - `--recreate / --no-recreate` (défaut: `--recreate`)

- `geosirene [dirname] [OPTIONS]`
  - Importe les établissements géolocalisés GeoSirene au format GeoParquet.
  - `dirname` est optionnel (télécharge le fichier GeoParquet national depuis data.gouv.fr par défaut).
  - Options :
    - `-d, --departement TEXT` (optionnel : limite l'import au département spécifié)
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `geosirene_etablissement`)
    - `--recreate / --no-recreate` (défaut: `--recreate`)

- `cartofriches [dirname] [OPTIONS]`
  - Importe les sites référencés dans Cartofriches (friches industrielles, commerciales, etc.).
  - `dirname` est optionnel (télécharge le fichier GeoPackage national depuis data.gouv.fr par défaut).
  - Options :
    - `--schema TEXT` (défaut: `public`)
    - `--table-name TEXT` (défaut: `friches_cartofriches`)
    - `--recreate / --no-recreate` (défaut: `--recreate`)

### Exemples

```shell
# Aide générale
docker compose run --rm urbaflow python urbaflow/main.py --help

# Commande MAJIC (toutes les étapes)
docker compose run --rm urbaflow python urbaflow/main.py majic /data/

# Risques cavités pour un département
docker compose run --rm urbaflow python urbaflow/main.py risques-cavite -d 85

# Bâti BD TOPO IGN sur un département entier
docker compose run --rm urbaflow python urbaflow/main.py bdtopo-batiment -d 35

# Bâti BD TOPO IGN sur toutes les communes d'un EPCI
docker compose run --rm urbaflow python urbaflow/main.py bdtopo-batiment -e 243500139

# PLU du Géoportail de l'Urbanisme pour un EPCI
docker compose run --rm urbaflow python urbaflow/main.py gpu-plu -e 200071629

# PLU du Géoportail de l'Urbanisme pour une commune
docker compose run --rm urbaflow python urbaflow/main.py gpu-plu -c 85047

# Bâti BD TOPO IGN sur une liste de communes
docker compose run --rm urbaflow python urbaflow/main.py bdtopo-batiment -c 35238,35047

# OCS GE IGN sur un département entier
docker compose run --rm urbaflow python urbaflow/main.py ocsge -d 35

# OCS GE IGN sur toutes les communes d'un EPCI
docker compose run --rm urbaflow python urbaflow/main.py ocsge -e 243500139

# LOVAC FIL avec options
docker compose run --rm urbaflow python urbaflow/main.py lovac-fil /data/ --schema public --table-name lovac_fil --recursive --recreate
```
## Licence

© Thomas Brosset - [thoomasbro](https://github.com/thoomasbro) - [KADATA](https://kadata.fr) - 2025
© Pierre Camilleri - [pierrecamilleri](https://github.com/pierrecamilleri) - [Multi](https://multi.coop) - 2023

Ce logiciel est distribué sous la licence CeCILL v2.1, compatible avec le droit français. Vous pouvez utiliser, modifier et distribuer ce logiciel selon les termes de la licence CeCILL. Toute modification ou distribution de ce logiciel doit être soumise aux mêmes conditions. Pour plus de détails, veuillez consulter le texte complet de la licence CeCILL à l'adresse suivante : [http://www.cecill.info/licences/Licence_CeCILL_V2.1-fr.html](http://www.cecill.info/licences/Licence_CeCILL_V2.1-fr.html). English version: [https://spdx.org/licenses/CECILL-2.1.html#licenseText](https://spdx.org/licenses/CECILL-2.1.html#licenseText)

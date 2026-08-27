import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from prefect import flow, task
from shared_tasks.config import TEMP_DIR
from shared_tasks.db_engine import create_engine
from shared_tasks.etl_gpd_utils import load
from shared_tasks.file_utils import encode_to_utf8, list_files_at_path
from shared_tasks.logging_config import get_logger
from sqlalchemy import DDL

# Données Géorisques SUP (Servitudes d'Utilité Publique)
# API Web service: https://www.georisques.gouv.fr/webappReport/ws/infosols/resultats/recherche?type=classification&statut=SUP&codeDepartement=85

logger = get_logger(__name__)


@task
def create_table_sup(
    schema: str = "public", table_name: str = "risques_sup", recreate: bool = True
):
    """
    Crée la table PostGIS pour les données SUP (Servitudes d'Utilité Publique).
    """
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        if recreate:
            conn.execute(DDL(f"DROP TABLE IF EXISTS {q(schema)}.{q(table_name)}"))
            logger.info(
                "Suppression de la table %s.%s si elle existe", schema, table_name
            )

        conn.execute(
            DDL(
                f"""
                CREATE TABLE IF NOT EXISTS {q(schema)}.{q(table_name)} (
                    identifiant_ssp text PRIMARY KEY,
                    identifiant_sis text,
                    statut text,
                    statut_definition text,
                    nom_usuel text,
                    code_insee text,
                    nom_commune text,
                    code_departement text,
                    nom_departement text,
                    code_region text,
                    nom_region text,
                    adresse text,
                    numero_voie text,
                    code_postal text,
                    complement_adresse text,
                    date_maj date,
                    url_fiche text,
                    bbox_geojson text
                )
                """
            )
        )
        logger.info(
            "Table %s.%s créée si elle n'existait pas auparavant", schema, table_name
        )


def parse_sup_item(item: dict, default_department: str | None = None) -> dict:
    """
    Transforme un objet JSON SUP renvoyé par l'API Géorisques en dictionnaire à plat.
    """
    identifiant_ssp = item.get("identifiantSsp")
    identifiant_sis = item.get("identifiantSis")

    statut_dto = item.get("statutClassificationDto") or {}
    statut = statut_dto.get("label") or "SUP"
    statut_definition = statut_dto.get("definition")

    nom_usuel = item.get("nomUsuel")

    communes = item.get("communeDtoList") or []
    code_insee_list = [c.get("code") for c in communes if c.get("code")]
    nom_commune_list = [c.get("nom") for c in communes if c.get("nom")]
    code_insee = ", ".join(dict.fromkeys(code_insee_list)) if code_insee_list else None
    nom_commune = (
        ", ".join(dict.fromkeys(nom_commune_list)) if nom_commune_list else None
    )

    first_commune = communes[0] if communes else {}
    dept_info = first_commune.get("departement") or {}
    region_info = dept_info.get("region") or {}

    code_departement = dept_info.get("code") or default_department
    nom_departement = dept_info.get("nom")
    code_region = region_info.get("code")
    nom_region = region_info.get("nom")

    adresses = item.get("adresseDtoList") or []
    rue_list = [a.get("rue") for a in adresses if a.get("rue")]
    numero_list = [a.get("numero") for a in adresses if a.get("numero")]
    cp_list = [a.get("codePostal") for a in adresses if a.get("codePostal")]
    complement_list = [
        a.get("complementAdresse") for a in adresses if a.get("complementAdresse")
    ]

    adresse = ", ".join(dict.fromkeys(rue_list)) if rue_list else None
    numero_voie = ", ".join(dict.fromkeys(numero_list)) if numero_list else None
    code_postal = ", ".join(dict.fromkeys(cp_list)) if cp_list else None
    complement_adresse = (
        ", ".join(dict.fromkeys(complement_list)) if complement_list else None
    )

    date_maj_raw = item.get("dateMaj")
    date_maj = None
    if isinstance(date_maj_raw, (int, float)):
        date_maj = datetime.fromtimestamp(
            date_maj_raw / 1000.0, tz=timezone.utc
        ).strftime("%Y-%m-%d")

    url_fiche = (
        f"https://fiches-risques.brgm.fr/georisques/infosols/classification/{identifiant_ssp}"
        if identifiant_ssp
        else None
    )

    bbox = item.get("bboxInstruction")
    bbox_geojson = json.dumps(bbox) if bbox else None

    return {
        "identifiant_ssp": identifiant_ssp,
        "identifiant_sis": identifiant_sis,
        "statut": statut,
        "statut_definition": statut_definition,
        "nom_usuel": nom_usuel,
        "code_insee": code_insee,
        "nom_commune": nom_commune,
        "code_departement": code_departement,
        "nom_departement": nom_departement,
        "code_region": code_region,
        "nom_region": nom_region,
        "adresse": adresse,
        "numero_voie": numero_voie,
        "code_postal": code_postal,
        "complement_adresse": complement_adresse,
        "date_maj": date_maj,
        "url_fiche": url_fiche,
        "bbox_geojson": bbox_geojson,
    }


@task
def load_sup(
    records: list[dict], schema: str = "public", table_name: str = "risques_sup"
):
    """
    Insère la liste des enregistrements SUP dans la table PostGIS spécifiée.
    """
    if not records:
        logger.info("Aucun enregistrement SUP à insérer.")
        return

    df = pd.DataFrame(records)
    df["identifiant_ssp"] = df["identifiant_ssp"].astype(str)
    df = df.drop_duplicates(subset=["identifiant_ssp"])

    e = create_engine()
    with e.begin() as conn:
        load(
            df,
            connection=conn,
            table_name=table_name,
            how="append",
            schema=schema,
            logger=logger,
        )


@task
def add_geometry_column_to_table(
    schema: str = "public", table_name: str = "risques_sup"
):
    """
    Ajoute la colonne de géométrie PostGIS geom et l'index spatial GIST associé.
    """
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        conn.execute(
            DDL(
                f"""
                ALTER TABLE {q(schema)}.{q(table_name)} 
                    ADD COLUMN IF NOT EXISTS 
                    geom geometry(GEOMETRY, 2154);
                CREATE INDEX IF NOT EXISTS {q(f"sidx_{table_name}_geom")}
                    ON {q(schema)}.{q(table_name)} USING GIST (geom);
                """
            )
        )


@task
def populate_geom(schema: str = "public", table_name: str = "risques_sup"):
    """
    Transforme le polygone GeoJSON (EPSG:3857)
    en géométrie PostGIS Lambert 93 (EPSG:2154).
    """
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        conn.execute(
            DDL(
                f"""
                UPDATE {q(schema)}.{q(table_name)}
                SET geom = ST_Multi(ST_Transform(
                    ST_SetSRID(ST_GeomFromGeoJSON(bbox_geojson), 3857),
                    2154
                ))
                WHERE bbox_geojson IS NOT NULL AND bbox_geojson != '';
                """
            )
        )


@task
def fetch_sup_data(department: str) -> list[dict]:
    """
    Récupère la totalité des données SUP via l'API Web service de Géorisques
    pour un département.
    """
    all_items = []
    page = 0
    size = 100

    while True:
        url = (
            "https://www.georisques.gouv.fr/webappReport/ws/infosols/resultats/recherche"
            f"?type=classification&statut=SUP&codeDepartement={department}&page={page}&size={size}"
        )
        logger.info(
            "Téléchargement de la page %d pour le département SUP %s", page, department
        )
        response = requests.get(url)
        if response.status_code != 200:
            logger.error(
                "Erreur lors du téléchargement des données SUP (statut %d)",
                response.status_code,
            )
            break

        res_json = response.json()
        items = res_json.get("data", [])
        if not items:
            break

        all_items.extend(items)

        total_count = None
        count_info = res_json.get("x-total-count")
        if count_info and isinstance(count_info, list) and len(count_info) > 0:
            try:
                total_count = int(count_info[0].get("value"))
            except (ValueError, TypeError):
                pass

        if total_count is not None and len(all_items) >= total_count:
            break

        page += 1

    logger.info("Total d'éléments SUP récupérés : %d", len(all_items))
    return [parse_sup_item(item, default_department=department) for item in all_items]


@task
def import_sup_files(
    path: Path, schema: str = "public", table_name: str = "risques_sup"
):
    """
    Importe les fichiers JSON SUP locaux présents dans un répertoire.
    """
    files = list_files_at_path(path, r".*sup.*|.*result.*", extension=".json")
    if not files:
        files = list_files_at_path(path, r".*", extension=".json")
    logger.info("Trouvé %d fichier(s) JSON à importer", len(files))

    all_records = []
    for file in files:
        complete_file_path = os.path.join(path, file)
        encode_to_utf8(complete_file_path)
        logger.info("Lecture du fichier : %s", file)
        with open(complete_file_path, encoding="utf-8") as f:
            content = json.load(f)
            items = content if isinstance(content, list) else content.get("data", [])
            for item in items:
                all_records.append(parse_sup_item(item))

    load_sup(all_records, schema=schema, table_name=table_name)


@flow
def import_risques_sup_flow(
    path: Path | None = None,
    department: str | None = None,
    schema: str = "public",
    table_name: str = "risques_sup",
    recreate: bool = False,
):
    """
    Flow d'importation des données SUP (Servitudes d'Utilité Publique).
    Si le répertoire local (path) n'est pas fourni, le département est spécifié
    pour télécharger les données depuis l'API Géorisques.
    """
    if path is None and department is None:
        raise ValueError("Le chemin du répertoire ou le département doit être fourni.")

    create_table_sup(schema=schema, table_name=table_name, recreate=recreate)
    add_geometry_column_to_table(schema=schema, table_name=table_name)

    if path is None:
        logger.info(
            "Téléchargement et importation des données SUP pour le département %s",
            department,
        )
        target_dir = TEMP_DIR / "georisques/sup" / department
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / f"sup_{department}.json"

        records = fetch_sup_data(department)
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        load_sup(records, schema=schema, table_name=table_name)
    else:
        logger.info("Importation des fichiers SUP depuis le répertoire %s", path)
        import_sup_files(path, schema=schema, table_name=table_name)

    populate_geom(schema=schema, table_name=table_name)

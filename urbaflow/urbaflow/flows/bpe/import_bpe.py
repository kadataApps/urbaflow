import zipfile
from pathlib import Path

import pandas as pd
import requests
from prefect import flow, task
from shared_tasks.config import TEMP_DIR
from shared_tasks.db_engine import create_engine
from shared_tasks.etl_gpd_utils import load
from shared_tasks.file_utils import encode_to_utf8, list_files_at_path
from shared_tasks.logging_config import get_logger
from sqlalchemy import DDL, text

# Base Permanente des Équipements (BPE / INSEE)
# URL de téléchargement du millésime (INSEE BPE 2025) :
# https://www.insee.fr/fr/statistiques/fichier/8217525/BPE25.zip

logger = get_logger(__name__)

BPE_2025_URL = "https://www.insee.fr/fr/statistiques/fichier/8217525/BPE25.zip"


@task
def create_table_bpe(
    schema: str = "public", table_name: str = "insee_bpe", recreate: bool = True
):
    """
    Crée la table insee_bpe dans la base de données PostGIS.
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
                    id text PRIMARY KEY,
                    an text,
                    apet text,
                    nomrs text,
                    cnomrs text,
                    numvoie text,
                    indrep text,
                    typvoie text,
                    libvoie text,
                    cadr text,
                    codpos text,
                    depcom text,
                    dep text,
                    reg text,
                    libcom text,
                    dom text,
                    sdom text,
                    typequ text,
                    siret text,
                    statut_diffusion text,
                    cantine text,
                    internat text,
                    rpi text,
                    ep text,
                    cl_pge text,
                    sect text,
                    secteur text,
                    acces_aire_pratique text,
                    acces_libre text,
                    acces_sanitaire text,
                    acces_vestiaire text,
                    capacite_d_accueil text,
                    pres_douche text,
                    pres_sanitaire text,
                    saisonnier text,
                    couvert text,
                    eclaire text,
                    categorie text,
                    multiplexe text,
                    structure_exercice text,
                    specialite text,
                    accueil text,
                    itinerance text,
                    mode_gestion text,
                    sstypheb text,
                    type text,
                    typeresto text,
                    implantation_station text,
                    gpl text,
                    capacite text,
                    indic_capa text,
                    nbequident text,
                    indic_nbequident text,
                    nbsalles text,
                    indic_nbsalles text,
                    nblieux text,
                    indic_nblieux text,
                    nb_pdc text,
                    indic_nb_pdc text,
                    nb_pdc_pa text,
                    indic_nb_pdc_pa text,
                    nb_pdc_acceleree text,
                    indic_nb_pdc_acceleree text,
                    nb_pdc_lente text,
                    indic_nb_pdc_lente text,
                    nb_pdc_rapide text,
                    indic_nb_pdc_rapide text,
                    nb_pdc_ultrarapide text,
                    indic_nb_pdc_ultrarapide text,
                    nb_jours_ouvert text,
                    indic_nb_jours_ouvert text,
                    lambert_x numeric,
                    lambert_y numeric,
                    longitude numeric,
                    latitude numeric,
                    qualite_xy text,
                    epsg text,
                    qualite_geoloc text,
                    tr_dist_precision text,
                    dciris text,
                    quali_iris text,
                    irisee text,
                    qp2024 text,
                    quali_qp2024 text,
                    qp2015 text,
                    quali_qp2015 text,
                    qva text,
                    quali_qva text,
                    zus text,
                    quali_zus text,
                    epci text,
                    uu2020 text,
                    bv2022 text,
                    aav2020 text,
                    dens3 text,
                    dens7 text
                )
                """
            )
        )
        logger.info(
            "Table %s.%s créée si elle n'existait pas auparavant", schema, table_name
        )


@task
def process_and_load_bpe(
    file_path: Path, schema: str = "public", table_name: str = "insee_bpe"
):
    """
    Lit le fichier CSV BPE, génère l'identifiant unique
    et l'insère par morceaux (chunks) dans PostGIS.
    """
    logger.info("Traitement et chargement du fichier BPE %s", file_path)
    encode_to_utf8(str(file_path))

    # Détection du séparateur
    with open(file_path, encoding="utf-8") as fp:
        first_line = fp.readline()
    sep = ";" if ";" in first_line else ","

    chunk_size = 100000
    reader = pd.read_csv(
        file_path,
        sep=sep,
        encoding="utf-8",
        dtype=str,
        chunksize=chunk_size,
        low_memory=False,
    )

    e = create_engine()
    total_inserted = 0

    for i, chunk in enumerate(reader):
        # Renommage des colonnes en minuscules
        chunk.columns = [c.lower() for c in chunk.columns]

        # Génération d'une clé primaire unique pour chaque équipement (ex: 1, 2, 3...)
        chunk["id"] = [(i * chunk_size + j + 1) for j in range(len(chunk))]
        chunk["id"] = chunk["id"].astype(str)

        # Conversion numérique des coordonnées
        for num_col in ["lambert_x", "lambert_y", "longitude", "latitude"]:
            if num_col in chunk.columns:
                chunk[num_col] = pd.to_numeric(chunk[num_col], errors="coerce")

        with e.begin() as conn:
            load(
                chunk,
                connection=conn,
                table_name=table_name,
                schema=schema,
                how="append",
                logger=logger,
            )

        total_inserted += len(chunk)
        logger.info(
            "Segment %d inséré (%d lignes, total cumule: %d)",
            i + 1,
            len(chunk),
            total_inserted,
        )


@task
def add_geometry_column_to_table(
    schema: str = "public", table_name: str = "insee_bpe"
):
    """
    Ajoute la colonne géométrique geom (Lambert 93 / EPSG:2154) et l'index spatial GIST.
    """
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        conn.execute(
            DDL(
                f"""
                ALTER TABLE {q(schema)}.{q(table_name)} 
                    ADD COLUMN IF NOT EXISTS 
                    geom geometry(POINT, 2154);
                CREATE INDEX IF NOT EXISTS {q(f"sidx_{table_name}_geom")}
                    ON {q(schema)}.{q(table_name)} USING GIST (geom);
                """
            )
        )


@task
def populate_geom(schema: str = "public", table_name: str = "insee_bpe"):
    """
    Alimente la colonne geom (EPSG:2154) à partir des coordonnées (longitude, latitude).
    """
    logger.info("Alimentation de la géométrie geom en Lambert 93 (EPSG:2154)...")
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        conn.execute(
            text(
                f"""
                UPDATE {q(schema)}.{q(table_name)}
                SET geom = ST_Transform(
                    ST_SetSRID(ST_MakePoint(longitude, latitude), 4326),
                    2154
                )
                WHERE longitude IS NOT NULL AND latitude IS NOT NULL;
                """
            )
        )


@flow
def import_bpe_flow(
    dirname: Path | None = None,
    db_schema: str = "public",
    table_name: str = "insee_bpe",
    recreate: bool = True,
):
    """
    Flow d'importation de la Base Permanente des Équipements (BPE / INSEE).
    Télécharge et intègre l'ensemble de la base géolocalisée de l'INSEE dans PostGIS.
    """
    create_table_bpe(schema=db_schema, table_name=table_name, recreate=recreate)
    add_geometry_column_to_table(schema=db_schema, table_name=table_name)

    if dirname is None:
        logger.info("Téléchargement de la base BPE INSEE depuis %s", BPE_2025_URL)
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        }
        target_dir = TEMP_DIR / "bpe"
        target_dir.mkdir(parents=True, exist_ok=True)
        zip_path = target_dir / "BPE.zip"

        response = requests.get(BPE_2025_URL, headers=headers, stream=True)
        response.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=65536):
                f.write(chunk)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(target_dir)
        logger.info("Extraction réussie dans %s", target_dir)
        dirname = target_dir

    csv_files = list_files_at_path(dirname, r".*bpe.*", extension=".csv")
    if not csv_files:
        csv_files = list_files_at_path(dirname, r".*", extension=".csv")

    if not csv_files:
        raise ValueError(f"Aucun fichier CSV BPE trouvé dans {dirname}")

    for file_path in csv_files:
        process_and_load_bpe(
            file_path=Path(file_path), schema=db_schema, table_name=table_name
        )

    populate_geom(schema=db_schema, table_name=table_name)

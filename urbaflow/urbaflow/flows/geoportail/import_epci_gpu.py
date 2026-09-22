import geopandas as gpd
import pandas as pd
import requests
from prefect import flow, task
from shared_tasks.db_engine import create_engine
from shared_tasks.etl_gpd_utils import (
    create_table_from_geodataframe,
    load,
)
from shared_tasks.logging_config import get_logger
from sqlalchemy import DDL, text

# API APICARTO IGN (GPU)
# Municipality : https://apicarto.ign.fr/api/gpu/municipality?insee={code_insee}
# Endpoints partitions : https://apicarto.ign.fr/api/gpu/{endpoint}?partition={partition}

logger = get_logger(__name__)

APICARTO_BASE_URL = "https://apicarto.ign.fr/api/gpu"

GPU_ENDPOINTS = [
    "zone-urba",
    "secteur-cc",
    "prescription-surf",
    "prescription-lin",
    "prescription-pct",
    "info-surf",
    "info-lin",
    "info-pct",
]


@task
def extract_epci_communes_from_db(
    siren_epci: str,
    schema: str = "public",
    table_name: str = "banatic_communes",
) -> pd.DataFrame:
    """
    Extrait de la table banatic_communes les communes de l'EPCI.
    """
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        query = text(
            f"SELECT * FROM {q(schema)}.{q(table_name)} WHERE siren_epci = :siren_epci"
        )
        df = pd.read_sql(query, conn, params={"siren_epci": str(siren_epci).strip()})

    if df.empty:
        logger.warning(
            "Aucune commune trouvée pour l'EPCI SIREN %s dans %s.%s",
            siren_epci,
            schema,
            table_name,
        )
    else:
        logger.info("Trouvé %d commune(s) pour l'EPCI SIREN %s", len(df), siren_epci)
    return df


@task
def enrich_communes_with_apicarto(df_communes: pd.DataFrame) -> pd.DataFrame:
    """
    Enrichit le DataFrame des communes via l'API /api/gpu/municipality
    (is_rnu, is_coastline).
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    df_enriched = df_communes.copy()

    is_rnu_list = []
    is_coastline_list = []

    for _, row in df_enriched.iterrows():
        code_insee = str(row["code_insee"]).strip().zfill(5)
        url = f"{APICARTO_BASE_URL}/municipality?insee={code_insee}"
        logger.info("Interrogation APICARTO municipality pour INSEE %s", code_insee)

        is_rnu = None
        is_coastline = None
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                features = data.get("features", [])
                if features:
                    props = features[0].get("properties", {})
                    is_rnu = props.get("is_rnu")
                    is_coastline = props.get("is_coastline")
            else:
                logger.warning(
                    "Code statut %d reçu pour la commune INSEE %s",
                    resp.status_code,
                    code_insee,
                )
        except Exception as err:
            logger.error(
                "Erreur lors de l'appel APICARTO municipality pour %s: %s",
                code_insee,
                err,
            )

        is_rnu_list.append(is_rnu)
        is_coastline_list.append(is_coastline)

    df_enriched["is_rnu"] = is_rnu_list
    df_enriched["is_coastline"] = is_coastline_list
    return df_enriched


@task
def create_epci_communes_table(
    df: pd.DataFrame,
    siren_epci: str,
    schema: str = "public",
):
    """
    Crée et remplit la table banatic_communes_{siren_epci}.
    """
    table_name = f"banatic_communes_{siren_epci}"
    e = create_engine()
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        conn.execute(DDL(f"DROP TABLE IF EXISTS {q(schema)}.{q(table_name)}"))
        logger.info("Création de la table %s.%s", schema, table_name)

        conn.execute(
            DDL(
                f"""
                CREATE TABLE {q(schema)}.{q(table_name)} (
                    code_insee text PRIMARY KEY,
                    siren_commune text,
                    nom_commune text,
                    code_departement text,
                    code_region text,
                    siren_epci text,
                    nom_epci text,
                    nature_juridique_epci text,
                    mode_financement_epci text,
                    nb_membres_epci integer,
                    total_pop_tot_epci integer,
                    total_pop_mun_epci integer,
                    pop_tot_commune integer,
                    pop_mun_commune integer,
                    is_rnu boolean,
                    is_coastline boolean
                )
                """
            )
        )

        load(
            df,
            connection=conn,
            table_name=table_name,
            how="append",
            schema=schema,
            logger=logger,
            nullable_integer_columns=[
                "nb_membres_epci",
                "total_pop_tot_epci",
                "total_pop_mun_epci",
                "pop_tot_commune",
                "pop_mun_commune",
            ],
        )


def fetch_apicarto_features(endpoint: str, partition: str) -> list[dict]:
    """
    Appelle l'API APICARTO IGN pour un endpoint et une partition.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"{APICARTO_BASE_URL}/{endpoint}?partition={partition}"
    try:
        resp = requests.get(url, headers=headers, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("features", [])
        else:
            logger.debug(
                "API APICARTO %s pour partition %s a retourné le code statut %d",
                endpoint,
                partition,
                resp.status_code,
            )
    except Exception as err:
        logger.error("Erreur d'appel APICARTO %s pour %s: %s", endpoint, partition, err)
    return []


@task
def update_gpu_table_for_epci(
    endpoint: str,
    insee_list: list[str],
    siren_epci: str,
    schema: str = "public",
):
    """
    Met à jour la table PostGIS gpu_{endpoint_with_underscore}.
    """
    table_name = f"gpu_{endpoint.replace('-', '_')}"
    e = create_engine()

    # 1. Vérification / Création de la table PostGIS destination si absente
    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        table_exists = conn.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                "WHERE table_schema = :schema AND table_name = :table)"
            ),
            {"schema": schema, "table": table_name},
        ).scalar()

        if not table_exists:
            logger.info("Création de la table %s.%s", schema, table_name)
            conn.execute(
                DDL(
                    f"""
                    CREATE TABLE {q(schema)}.{q(table_name)} (
                        gid text PRIMARY KEY,
                        partition text,
                        insee text,
                        gpu_doc_id text,
                        gpu_status text,
                        gpu_timestamp text,
                        libelle text,
                        txt text,
                        typezone text,
                        stypepsc text,
                        typepsc text,
                        datappro text,
                        datvalid text,
                        idurba text,
                        idzone text,
                        lib_idzone text,
                        idpsc text,
                        lib_idpsc text,
                        nomfic text,
                        urlfic text,
                        geom geometry(GEOMETRY, 2154)
                    )
                    """
                )
            )
            conn.execute(
                DDL(
                    f"""
                    CREATE INDEX IF NOT EXISTS {q(f"sidx_{table_name}_geom")}
                        ON {q(schema)}.{q(table_name)} USING GIST (geom);
                    """
                )
            )

    # 2. Suppression des données existantes pour les partitions cibles
    partitions_to_clean = []
    for code_insee in insee_list:
        partitions_to_clean.extend([f"DU_{code_insee}", f"PSMV_{code_insee}"])
    partitions_to_clean.extend([f"DU_{siren_epci}", f"PSMV_{siren_epci}"])

    with e.begin() as conn:
        q = conn.engine.dialect.identifier_preparer.quote
        logger.info(
            "Suppression des données dans %s.%s pour les partitions de l'EPCI %s",
            schema,
            table_name,
            siren_epci,
        )
        conn.execute(
            text(
                f"DELETE FROM {q(schema)}.{q(table_name)} "
                "WHERE partition = ANY(:partitions)"
            ),
            {"partitions": partitions_to_clean},
        )

    # 3. Récupération des nouvelles données auprès de l'API APICARTO IGN
    all_features = []

    # Pour chaque commune
    for code_insee in insee_list:
        for prefix in ["DU", "PSMV"]:
            partition = f"{prefix}_{code_insee}"
            feats = fetch_apicarto_features(endpoint, partition)
            if feats:
                logger.info(
                    "Trouvé %d feature(s) pour %s sur %s",
                    len(feats),
                    endpoint,
                    partition,
                )
                all_features.extend(feats)

    # Pour le SIREN de l'EPCI
    for prefix in ["DU", "PSMV"]:
        partition = f"{prefix}_{siren_epci}"
        feats = fetch_apicarto_features(endpoint, partition)
        if feats:
            logger.info(
                "Trouvé %d feature(s) pour %s sur %s",
                len(feats),
                endpoint,
                partition,
            )
            all_features.extend(feats)

    if not all_features:
        logger.info(
            "Aucune donnée à insérer pour %s sur l'EPCI %s", endpoint, siren_epci
        )
        return

    # 4. Conversion GeoDataFrame & Chargement PostGIS
    gdf = gpd.GeoDataFrame.from_features(all_features, crs="EPSG:4326")
    gdf = gdf.to_crs("EPSG:2154")
    gdf = gdf.rename_geometry("geom")

    # Dédoublonnage sur gid si présent
    if "gid" in gdf.columns:
        gdf["gid"] = gdf["gid"].astype(str)
        gdf = gdf.drop_duplicates(subset=["gid"])
    else:
        gdf["gid"] = [str(i) for i in range(len(gdf))]

    logger.info(
        "Chargement de %d enregistrement(s) dans %s.%s",
        len(gdf),
        schema,
        table_name,
    )
    with e.begin() as conn:
        create_table_from_geodataframe(
            gdf=gdf,
            connection=conn,
            table_name=table_name,
            schema=schema,
            logger=logger,
            recreate=False,
            srs=2154,
        )
        existing_cols = (
            conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = :schema AND table_name = :table"
                ),
                {"schema": schema, "table": table_name},
            )
            .scalars()
            .all()
        )

        missing_cols = [c for c in gdf.columns if c not in existing_cols]
        for col in missing_cols:
            q = conn.engine.dialect.identifier_preparer.quote
            col_type = "numeric" if pd.api.types.is_numeric_dtype(gdf[col]) else "text"
            logger.info(
                "Ajout de la colonne %s (%s) dans %s.%s",
                col,
                col_type,
                schema,
                table_name,
            )
            conn.execute(
                DDL(
                    f"ALTER TABLE {q(schema)}.{q(table_name)} "
                    f"ADD COLUMN IF NOT EXISTS {q(col)} {col_type}"
                )
            )

        load(
            gdf,
            connection=conn,
            table_name=table_name,
            schema=schema,
            how="append",
            logger=logger,
        )


@flow
def import_epci_gpu_flow(
    siren_epci: str,
    db_schema: str = "public",
    banatic_table: str = "banatic_communes",
):
    """
    Flow d'intégration complet pour un EPCI à partir de son SIREN :
    1. Extrait la liste des communes de l'EPCI depuis banatic_communes.
    2. Enrichit les communes via /api/gpu/municipality (is_rnu, is_coastline).
    3. Crée la table banatic_communes_{siren_epci} dans PostGIS.
    4. Met à jour les 8 tables GPU (gpu_zone_urba, gpu_secteur_cc, etc.).
    """
    logger.info("Début de l'intégration EPCI SIREN : %s", siren_epci)

    # Step 1: Extraction des communes de l'EPCI depuis la BDD
    df_communes = extract_epci_communes_from_db(
        siren_epci=siren_epci, schema=db_schema, table_name=banatic_table
    )

    if df_communes.empty:
        raise ValueError(
            f"Aucune commune trouvée pour l'EPCI {siren_epci} dans "
            f"{db_schema}.{banatic_table}. Lancer d'abord 'banatic-communes'."
        )

    # Step 2: Enrichissement des communes via /api/gpu/municipality
    df_enriched = enrich_communes_with_apicarto(df_communes)

    # Step 3: Création de la table banatic_communes_{siren_epci}
    create_epci_communes_table(df=df_enriched, siren_epci=siren_epci, schema=db_schema)

    # Step 4: Mise à jour des tables GPU (zone-urba, secteur-cc, prescriptions, infos)
    insee_list = [
        str(c).strip().zfill(5) for c in df_enriched["code_insee"].unique() if c
    ]

    for endpoint in GPU_ENDPOINTS:
        logger.info("Traitement de l'endpoint GPU : %s", endpoint)
        update_gpu_table_for_epci(
            endpoint=endpoint,
            insee_list=insee_list,
            siren_epci=str(siren_epci).strip(),
            schema=db_schema,
        )

    logger.info("Intégration EPCI SIREN %s terminée avec succès !", siren_epci)

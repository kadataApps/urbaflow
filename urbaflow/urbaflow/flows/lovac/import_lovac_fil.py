import logging
from pathlib import Path
import pandas as pd
from sqlalchemy import DDL, text

from shared_tasks.etl_gpd_utils import load
from shared_tasks.db_engine import create_engine

# https://doc-datafoncier.cerema.fr/doc/lovac/
# https://doc-datafoncier.cerema.fr/doc/guide/lovac

logger = logging.getLogger(__name__)


def find_lovac_files(dirname: Path, recursive: bool = True) -> list[Path]:
    """
    Find all files in the directory that match the pattern 'lovac_fil.CSV|csv'

    Args:
        dirname: Directory to search in
        recursive: If True, search recursively in subdirectories (default: True)

    Returns:
        list[Path]: List of found lovac_fil files (without duplicates)
    """
    # Example filename: lovac_fil.csv or lovac_fil.CSV
    csv_files = set()  # Use set to avoid duplicates

    if recursive:
        # Search recursively in all subdirectories
        csv_files.update(dirname.rglob("lovac_fil.csv"))
        csv_files.update(dirname.rglob("lovac_fil.CSV"))
    else:
        # Search only in the current directory
        csv_files.update(dirname.glob("lovac_fil.csv"))
        csv_files.update(dirname.glob("lovac_fil.CSV"))

    # Convert set back to sorted list
    csv_files = sorted(list(csv_files))

    if len(csv_files) == 0:
        search_type = "recursively" if recursive else "in directory"
        raise FileNotFoundError(
            f"No files found {search_type} in {dirname} that match the pattern 'lovac_fil.CSV|csv'"
        )

    logger.info(
        f"Found {len(csv_files)} lovac_fil files in {dirname} (recursive={recursive})"
    )
    for file in csv_files:
        logger.info(f"  - {file}")

    return csv_files


def extract_lovac_data(file: Path) -> pd.DataFrame:
    """
    Extract the data from the lovac_fil.csv file and sanitize missing values.

    The file is pipe-delimited (|) and contains data about vacant commercial properties.
    This function reads the CSV file, loads it into a DataFrame, and cleans missing values.

    Args:
        file: Path to the lovac_fil.csv file

    Returns:
        pd.DataFrame: Cleaned DataFrame with sanitized missing values

    Example content:
      annee|ff_millesime|dir|sip|cer_local_occ|invariant|ff_idlocal|ff_idbat|ff_idpar|ff_idsec|refcad|loc_num|loc_voie|libvoie|batloc|rnb_id|rnb_id_score|libcom|commune|ff_idcom|cog_2025|intercommunalite|ccodep|ban_result_score|ban_result_label|ban_result_postcode|ban_result_id|ban_latitude|ban_longitude|distance_ban_ff|ff_x|ff_y|ff_x_4326|ff_y_4326|nature|ff_ctpdl|ff_stoth|ff_slocal|ff_npiece_p2|ff_jannath|ff_dnbbai|ff_dnbdou|ff_dnbwc|ff_dcapec2|ff_ndroit|ff_dcntpa|vlcad|vl_revpro|ff_dvltrt|aff|anrefthlv|txtlv|potentiel_tlv_thlv|ff_ccthp|ffh_ccthp|debutvacance|cer_h1767|anmutation|ff_jdatat|ffh_jdatat|dvf_datemut|dvf_nblocmut|dvf_nblog|dvf_valeurfonc|dvf_idmutation|dvf_libnatmut|dvf_vefa|dvf_codtypbien|dvf_libtypbien|dvf_filtre|dvf_codtypprov|dvf_codtypproa|gestre_ppre|proprietaire|cer_propriétaire|cer_gestionnaire|adresse1|adresse2|adresse3|adresse4|groupe|ff_idprocpte|ff_idprodroit_1|ff_idpersonne_1|ff_jdatnss_1|ff_dldnss_1|ff_ddenom_1|ff_dsiren_1|ff_ccogrm_1|ff_catpro2txt_1|ff_catpro3_1|ff_ccodro_1|ff_locprop_1|cer_ff_adresse_1|ff_idprodroit_2|ff_idpersonne_2|ff_jdatnss_2|ff_dldnss_2|ff_ddenom_2|ff_dsiren_2|ff_ccogrm_2|ff_catpro2txt_2|ff_catpro3_2|ff_ccodro_2|ff_locprop_2|cer_ff_adresse_2|ff_idprodroit_3|ff_idpersonne_3|ff_jdatnss_3|ff_dldnss_3|ff_ddenom_3|ff_dsiren_3|ff_ccogrm_3|ff_catpro2txt_3|ff_catpro3_3|ff_ccodro_3|ff_locprop_3|cer_ff_adresse_3|ff_idprodroit_4|ff_idpersonne_4|ff_jdatnss_4|ff_ddenom_4|ff_dldnss_4|ff_dsiren_4|ff_ccogrm_4|ff_catpro2txt_4|ff_catpro3_4|ff_ccodro_4|ff_locprop_4|cer_ff_adresse_4|ff_idprodroit_5|ff_idpersonne_5|ff_jdatnss_5|ff_dldnss_5|ff_ddenom_5|ff_dsiren_5|ff_ccogrm_5|ff_catpro2txt_5|ff_catpro3_5|ff_ccodro_5|ff_locprop_5|cer_ff_adresse_5|ff_idprodroit_6|ff_idpersonne_6|ff_jdatnss_6|ff_dldnss_6|ff_ddenom_6|ff_dsiren_6|ff_ccogrm_6|ff_catpro2txt_6|ff_catpro3_6|ff_ccodro_6|ff_locprop_6|cer_ff_adresse_6
      2025|2024|760|1080|1|I3770078924L|763770078924|763770000A0750A|763770000A0750|763770000A|A0750|1138|275|1138   RTE DE LA MUETTE|A010001001|Z8DGX3HA2WZ7|3|ISNEAUVILLE|377|76377|76377|U759|76||||||||565175.1396114496|6935840.272408655|1.13906341592369|49.50760332407065|MAISON||84|177|4|1966|1.0|0.0|1.0|5|2|5117|492|0|492|H|2022|||V|P-P-P-P-P-P-P-P-P-P-P-V-P-V-V|2022|O-V-V-O-V-V|2020-12-31|2020-12-31|1970-01-01,2009-01-12,2020-12-31|2019-09-16|1.0|1.0|130000.0|16287940.0|Vente|False|1113.0|UNE MAISON ANCIENNE|0.0|X1||M MEHAMMEDIA DJILALI||M MEHAMMEDIA DJILALI||280 RTE DE DIEPPE|||76250 DEVILLE LES ROUEN| |76377M00220|76377M0022001|76MCWJNF|1980-08-17|99 ALGERIE(GUELMA)|MEHAMMEDIA DJILALI|||PERSONNE PHYSIQUE|X1a|P|2|0280 RTE DE DIEPPE 76250 DEVILLE LES ROUEN|76377M0022002|76MCWJNH|1988-09-06|76 MONT-SAINT-AIGNAN|BEN AHMED SOUAD|||PERSONNE PHYSIQUE|X1a|P|2.0|0280 RTE DE DIEPPE 76250 DEVILLE LES ROUEN||||||||||||||||||||||||||||||||||||||||||||||||
    """
    try:
        logger.info(f"Reading LOVAC file: {file}")

        # Read the pipe-delimited CSV file
        df = pd.read_csv(
            file,
            sep="|",
            dtype=str,  # Read all columns as strings initially to preserve data integrity
            na_values=[
                "",
                " ",
                "NULL",
                "null",
                "None",
                "none",
            ],  # Define what should be considered as NaN
            keep_default_na=True,
        )

        logger.info(
            f"Successfully loaded {len(df)} rows and {len(df.columns)} columns from {file.name}"
        )

        # Clean and sanitize the data
        logger.info("Sanitizing missing values...")

        # Replace empty strings and whitespace-only strings with NaN
        # Fix for FutureWarning: explicitly call infer_objects to retain old behavior
        with pd.option_context("future.no_silent_downcasting", True):
            df = df.replace(r"^\s*$", pd.NA, regex=True)
            df = df.infer_objects(copy=False)

        # Convert specific numeric columns back to appropriate types
        numeric_columns = [
            "annee",
            "ff_millesime",
            "dir",
            "sip",
            "cer_local_occ",
            "ff_idcom",
            "loc_num",
            "loc_voie",
            "rnb_id_score",
            "commune",
            "ban_result_score",
            "ban_latitude",
            "ban_longitude",
            "distance_ban_ff",
            "ff_x",
            "ff_y",
            "ff_x_4326",
            "ff_y_4326",
            "ff_stoth",
            "ff_slocal",
            "ff_npiece_p2",
            "ff_jannath",
            "ff_dnbbai",
            "ff_dnbdou",
            "ff_dnbwc",
            "ff_dcapec2",
            "ff_ndroit",
            "ff_dcntpa",
            "vlcad",
            "vl_revpro",
            "ff_dvltrt",
            "dvf_nblocmut",
            "dvf_nblog",
            "dvf_valeurfonc",
            "dvf_idmutation",
            "dvf_filtre",
            "ff_ccogrm_1",
            "ff_catpro3_1",
            "ff_locprop_1",
            "ff_ccogrm_2",
            "ff_catpro3_2",
            "ff_locprop_2",
            "ff_ccogrm_3",
            "ff_catpro3_3",
            "ff_locprop_3",
            "ff_ccogrm_4",
            "ff_catpro3_4",
            "ff_locprop_4",
            "ff_ccogrm_5",
            "ff_catpro3_5",
            "ff_locprop_5",
            "ff_ccogrm_6",
            "ff_catpro3_6",
            "ff_locprop_6",
        ]

        # Convert numeric columns, keeping NaN for missing values
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Convert date columns to datetime
        date_columns = [
            "ff_jdatat",
            "dvf_datemut",
            "ff_jdatnss_1",
            "ff_jdatnss_2",
            "ff_jdatnss_3",
            "ff_jdatnss_4",
            "ff_jdatnss_5",
            "ff_jdatnss_6",
        ]

        for col in date_columns:
            if col in df.columns:
                # Handle different date formats that might be present
                # Fix for UserWarning: specify format to avoid dateutil fallback
                try:
                    # Try common date formats first
                    df[col] = pd.to_datetime(
                        df[col], format="%Y-%m-%d", errors="coerce"
                    )
                except (ValueError, TypeError):
                    try:
                        df[col] = pd.to_datetime(
                            df[col], format="%d/%m/%Y", errors="coerce"
                        )
                    except (ValueError, TypeError):
                        df[col] = pd.to_datetime(df[col], errors="coerce")

        # Convert boolean columns
        boolean_columns = ["dvf_vefa"]
        for col in boolean_columns:
            if col in df.columns:
                df[col] = df[col].map(
                    {"True": True, "False": False, True: True, False: False}
                )

        # Log data quality information
        total_cells = df.size
        missing_cells = df.isna().sum().sum()
        missing_percentage = (missing_cells / total_cells) * 100

        logger.info("Data quality summary:")
        logger.info(f"  - Total cells: {total_cells:,}")
        logger.info(f"  - Missing cells: {missing_cells:,} ({missing_percentage:.2f}%)")
        logger.info(f"  - Columns with missing values: {df.isna().any().sum()}")

        # Log columns with high percentage of missing values (>50%)
        missing_by_column = df.isna().sum() / len(df) * 100
        high_missing_cols = missing_by_column[missing_by_column > 50]
        if len(high_missing_cols) > 0:
            logger.warning(
                f"Columns with >50% missing values: {list(high_missing_cols.index)}"
            )

        return df

    except Exception as e:
        logger.error(f"Error reading LOVAC file {file}: {str(e)}")
        raise


def create_table_lovac_fil(
    schema: str = "public", table_name: str = "lovac_fil", recreate: bool = False
):
    """
    Create the lovac_fil table in the database.

    Args:
        schema: Database schema name (default: "public")
        table_name: Table name (default: "lovac_fil")
        recreate: If True, drop/recreate table (default: False)
    """
    logger.info(f"Managing table {schema}.{table_name} (recreate={recreate})")

    e = create_engine()
    with e.begin() as conn:
        if recreate:
            conn.execute(text(f"DROP TABLE IF EXISTS {schema}.{table_name};"))
            logger.info(f"Successfully dropped table {schema}.{table_name}")

        # create table (default behavior or when table doesn't exist)
        logger.info(f"Creating table {schema}.{table_name}")
        conn.execute(
            DDL(
                f"""
                CREATE TABLE IF NOT EXISTS {schema}.{table_name} (
                    annee INTEGER,
                    ff_millesime INTEGER,
                    dir INTEGER,
                    sip INTEGER,
                    cer_local_occ INTEGER,
                    invariant TEXT,
                    ff_idlocal TEXT,
                    ff_idbat TEXT,
                    ff_idpar TEXT,
                    ff_idsec TEXT,
                    refcad TEXT,
                    loc_num INTEGER,
                    loc_voie INTEGER,
                    libvoie TEXT,
                    batloc TEXT,
                    rnb_id TEXT,
                    rnb_id_score FLOAT,
                    libcom TEXT,
                    commune INTEGER,
                    ff_idcom INTEGER,
                    cog_2025 TEXT,
                    intercommunalite TEXT,
                    ccodep TEXT,
                    ban_result_score FLOAT,
                    ban_result_label TEXT,
                    ban_result_postcode TEXT,
                    ban_result_id TEXT,
                    ban_latitude FLOAT,
                    ban_longitude FLOAT,
                    distance_ban_ff FLOAT,
                    ff_x FLOAT,
                    ff_y FLOAT,
                    ff_x_4326 FLOAT,
                    ff_y_4326 FLOAT,
                    nature TEXT,
                    ff_ctpdl TEXT,
                    ff_stoth INTEGER,
                    ff_slocal INTEGER,
                    ff_npiece_p2 INTEGER,
                    ff_jannath INTEGER,
                    ff_dnbbai FLOAT,
                    ff_dnbdou FLOAT,
                    ff_dnbwc FLOAT,
                    ff_dcapec2 INTEGER,
                    ff_ndroit INTEGER,
                    ff_dcntpa INTEGER,
                    vlcad INTEGER,
                    vl_revpro INTEGER,
                    ff_dvltrt INTEGER,
                    aff TEXT,
                    anrefthlv TEXT,
                    txtlv TEXT,
                    potentiel_tlv_thlv TEXT,
                    ff_ccthp TEXT,
                    ffh_ccthp TEXT,
                    debutvacance INTEGER,
                    cer_h1767 TEXT,
                    anmutation TEXT,
                    ff_jdatat TIMESTAMP,
                    ffh_jdatat TEXT,
                    dvf_datemut TIMESTAMP,
                    dvf_nblocmut FLOAT,
                    dvf_nblog FLOAT,
                    dvf_valeurfonc FLOAT,
                    dvf_idmutation FLOAT,
                    dvf_libnatmut TEXT,
                    dvf_vefa BOOLEAN,
                    dvf_codtypbien FLOAT,
                    dvf_libtypbien TEXT,
                    dvf_filtre FLOAT,
                    dvf_codtypprov TEXT,
                    dvf_codtypproa TEXT,
                    gestre_ppre TEXT,
                    proprietaire TEXT,
                    cer_propriétaire TEXT,
                    cer_gestionnaire TEXT,
                    adresse1 TEXT,
                    adresse2 TEXT,
                    adresse3 TEXT,
                    adresse4 TEXT,
                    groupe TEXT,
                    ff_idprocpte TEXT,
                    ff_idprodroit_1 TEXT,
                    ff_idpersonne_1 TEXT,
                    ff_jdatnss_1 TIMESTAMP,
                    ff_dldnss_1 TEXT,
                    ff_ddenom_1 TEXT,
                    ff_dsiren_1 TEXT,
                    ff_ccogrm_1 FLOAT,
                    ff_catpro2txt_1 TEXT,
                    ff_catpro3_1 FLOAT,
                    ff_ccodro_1 TEXT,
                    ff_locprop_1 FLOAT,
                    cer_ff_adresse_1 TEXT,
                    ff_idprodroit_2 TEXT,
                    ff_idpersonne_2 TEXT,
                    ff_jdatnss_2 TIMESTAMP,
                    ff_dldnss_2 TEXT,
                    ff_ddenom_2 TEXT,
                    ff_dsiren_2 TEXT,
                    ff_ccogrm_2 FLOAT,
                    ff_catpro2txt_2 TEXT,
                    ff_catpro3_2 FLOAT,
                    ff_ccodro_2 TEXT,
                    ff_locprop_2 FLOAT,
                    cer_ff_adresse_2 TEXT,
                    ff_idprodroit_3 TEXT,
                    ff_idpersonne_3 TEXT,
                    ff_jdatnss_3 TIMESTAMP,
                    ff_dldnss_3 TEXT,
                    ff_ddenom_3 TEXT,
                    ff_dsiren_3 TEXT,
                    ff_ccogrm_3 FLOAT,
                    ff_catpro2txt_3 TEXT,
                    ff_catpro3_3 FLOAT,
                    ff_ccodro_3 TEXT,
                    ff_locprop_3 FLOAT,
                    cer_ff_adresse_3 TEXT,
                    ff_idprodroit_4 TEXT,
                    ff_idpersonne_4 TEXT,
                    ff_jdatnss_4 TIMESTAMP,
                    ff_ddenom_4 TEXT,
                    ff_dldnss_4 TEXT,
                    ff_dsiren_4 TEXT,
                    ff_ccogrm_4 FLOAT,
                    ff_catpro2txt_4 TEXT,
                    ff_catpro3_4 FLOAT,
                    ff_ccodro_4 TEXT,
                    ff_locprop_4 FLOAT,
                    cer_ff_adresse_4 TEXT,
                    ff_idprodroit_5 TEXT,
                    ff_idpersonne_5 TEXT,
                    ff_jdatnss_5 TIMESTAMP,
                    ff_dldnss_5 TEXT,
                    ff_ddenom_5 TEXT,
                    ff_dsiren_5 TEXT,
                    ff_ccogrm_5 FLOAT,
                    ff_catpro2txt_5 TEXT,
                    ff_catpro3_5 FLOAT,
                    ff_ccodro_5 TEXT,
                    ff_locprop_5 FLOAT,
                    cer_ff_adresse_5 TEXT,
                    ff_idprodroit_6 TEXT,
                    ff_idpersonne_6 TEXT,
                    ff_jdatnss_6 TIMESTAMP,
                    ff_dldnss_6 TEXT,
                    ff_ddenom_6 TEXT,
                    ff_dsiren_6 TEXT,
                    ff_ccogrm_6 FLOAT,
                    ff_catpro2txt_6 TEXT,
                    ff_catpro3_6 FLOAT,
                    ff_ccodro_6 TEXT,
                    ff_locprop_6 FLOAT,
                    cer_ff_adresse_6 TEXT,
                    urbaflow_inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        )
    logger.info(f"Successfully managed table {schema}.{table_name}")


def load_lovac_fil_data(
    data: pd.DataFrame, schema: str = "public", table_name: str = "lovac_fil"
):
    """
    Load the LOVAC FIL data into the database.

    Args:
        data: Cleaned DataFrame containing LOVAC FIL data
        schema: Database schema name (default: "public")
        table_name: Table name (default: "lovac_fil")
    """
    logger.info(f"Loading {len(data)} rows into {schema}.{table_name}")

    # Add metadata columns
    data_copy = data.copy()
    data_copy["urbaflow_inserted_at"] = pd.Timestamp.now()

    e = create_engine()
    with e.begin() as conn:
        load(
            data_copy,
            connection=conn,
            table_name=table_name,
            how="append",
            schema=schema,
            logger=logger,
        )

    logger.info(f"Successfully loaded {len(data)} rows into {schema}.{table_name}")


def create_centroid_geometry(schema: str = "public", table_name: str = "lovac_fil"):
    """
    Create centroid geometry column in the lovac_fil table.

    Args:
        schema: Database schema name (default: "public")
        table_name: Table name (default: "lovac_fil")
    """
    logger.info(f"Creating centroid geometry column in {schema}.{table_name}")

    e = create_engine()
    with e.begin() as conn:
        # Add geometry column if it doesn't exist
        conn.execute(
            text(
                f"""
            ALTER TABLE {schema}.{table_name}
            ADD COLUMN IF NOT EXISTS geom_centroid GEOMETRY(POINT, 2154);
            """
            )
        )

        # Update geometry column with POINT from ff_x_4326 and ff_y_4326
        conn.execute(
            text(
                f"""
            UPDATE {schema}.{table_name}
            SET geom_centroid = ST_SetSRID(ST_MakePoint(ff_x, ff_y), 2154)
            WHERE ff_x IS NOT NULL AND ff_y IS NOT NULL;
            """
            )
        )

        # Create spatial index on the geometry column
        conn.execute(
            text(
                f"""
            CREATE INDEX IF NOT EXISTS idx_{table_name}_geom_centroid
            ON {schema}.{table_name} USING GIST (geom_centroid);
            """
            )
        )

    logger.info(
        f"Successfully created centroid geometry column in {schema}.{table_name}"
    )


def create_lovac_fil_parcelle_table(
    schema: str = "public",
    dst_table_name: str = "lovac_fil_parcelle",
    lovac_fil_table_name: str = "lovac_fil",
    parcelle_table_name: str = "parcellaire",
    recreate: bool = True,
):
    """
    Create the lovac_fil_parcelle table in the database.

    Args:
        schema: Database schema name (default: "public")
        table_name: Table name (default: "lovac_fil_parcelle")
        parcelle_table_name: Name of the parcellaire table to reference (default: "parcellaire")
        recreate: If True, drop/recreate table (default: False)
    """
    logger.info(f"Managing table {schema}.{dst_table_name} (recreate={recreate})")

    e = create_engine()
    with e.begin() as conn:
        if recreate:
            conn.execute(text(f"DROP TABLE IF EXISTS {schema}.{dst_table_name};"))
            logger.info(f"Successfully dropped table {schema}.{dst_table_name}")

            # create table (default behavior or when table doesn't exist)
            logger.info(f"Creating table {schema}.{dst_table_name}")
            conn.execute(
                DDL(
                    f"""
                    CREATE TABLE IF NOT EXISTS {schema}.{dst_table_name} AS 
                    SELECT a.ff_idpar,
                      ST_Multi(p.geom)::geometry(MultiPolygon,2154) AS geom,
                      a.nb_logt_vac,
                      a.debut_vacance_min,
                      a.debut_vacance_max,
                      now() AS urbaflow_inserted_at
                    FROM (
                      SELECT l.ff_idpar,
                            COUNT(*)               AS nb_logt_vac,
                            MIN(l.debutvacance)    AS debut_vacance_min,
                            MAX(l.debutvacance)    AS debut_vacance_max
                      FROM {schema}.{lovac_fil_table_name} AS l
                      GROUP BY l.ff_idpar
                    ) AS a
                    JOIN {schema}.{parcelle_table_name} AS p
                      ON p.idpar = a.ff_idpar
                    ;
                    """
                )
            )
            # Add primary key constraint
            conn.execute(
                text(
                    f"""
                ALTER TABLE {schema}.{dst_table_name}
                ADD CONSTRAINT pk_{dst_table_name} PRIMARY KEY (ff_idpar);
                """
                )
            )
            # Create spatial index on the geometry column
            conn.execute(
                text(
                    f"""
                CREATE INDEX IF NOT EXISTS idx_{dst_table_name}_geom
                ON {schema}.{dst_table_name} USING GIST (geom);
                """
                )
            )
        else:
            logger.info(
                f"Table {schema}.{dst_table_name} already exists. Skipping creation."
            )
            conn.execute(
                text(
                    f"""
                INSERT INTO {schema}.{dst_table_name}
                  (ff_idpar, geom, nb_logt_vac, debut_vacance_min, debut_vacance_max, urbaflow_inserted_at)
                SELECT a.ff_idpar,
                      ST_Multi(p.geom)::geometry(MultiPolygon,2154) AS geom,
                      a.nb_logt_vac,
                      a.debut_vacance_min,
                      a.debut_vacance_max,
                      now() AS urbaflow_inserted_at
                FROM (
                  SELECT l.ff_idpar,
                        COUNT(*)               AS nb_logt_vac,
                        MIN(l.debutvacance)    AS debut_vacance_min,
                        MAX(l.debutvacance)    AS debut_vacance_max
                  FROM {schema}.{lovac_fil_table_name} AS l
                  GROUP BY l.ff_idpar
                ) AS a
                JOIN {schema}.{parcelle_table_name} AS p
                  ON p.idpar = a.ff_idpar
                ON CONFLICT (ff_idpar) DO UPDATE
                SET geom               = EXCLUDED.geom,
                    nb_logt_vac        = EXCLUDED.nb_logt_vac,
                    debut_vacance_min  = EXCLUDED.debut_vacance_min,
                    debut_vacance_max  = EXCLUDED.debut_vacance_max,
                    urbaflow_inserted_at = EXCLUDED.urbaflow_inserted_at;
                """
                )
            )

    logger.info(f"Successfully managed table {schema}.{dst_table_name}")


def import_lovac_fil_flow(
    dirname: Path,
    schema: str = "public",
    table_name: str = "lovac_fil",
    recursive: bool = True,
    recreate: bool = False,
):
    """
    Complete flow to import LOVAC FIL data from CSV files.

    This flow orchestrates the entire process:
    1. Find lovac_fil.csv files in the specified directory
    2. Extract and clean data from each file
    3. Create the database table or truncate existing one
    4. Load all data into the database

    Args:
        dirname: Path to directory containing lovac_fil.csv files
        schema: Database schema name (default: "public")
        table_name: Table name (default: "lovac_fil")
        recursive: If True, search recursively in subdirectories (default: True)
        recreate: If True, drop and recreate the table (default: False)
    """
    logger.info(f"Starting LOVAC FIL import flow from {dirname}")

    # Step 1: Find all lovac_fil files in the directory
    files = find_lovac_files(dirname, recursive=recursive)
    logger.info(f"Found {len(files)} LOVAC FIL files to process")

    # Step 2: Create the database table (this will drop existing table if present)
    create_table_lovac_fil(schema=schema, table_name=table_name, recreate=recreate)

    # Step 3: Process each file and combine data
    all_data = []
    for file in files:
        logger.info(f"Processing file: {file.name}")
        data = extract_lovac_data(file)
        all_data.append(data)

    # Step 4: Combine all dataframes if multiple files
    if len(all_data) > 1:
        logger.info(f"Combining data from {len(all_data)} files")
        combined_data = pd.concat(all_data, ignore_index=True)
        logger.info(f"Combined dataset has {len(combined_data)} total rows")
    elif len(all_data) == 1:
        combined_data = all_data[0]
    else:
        logger.warning("No data found to load")
        return

    # Step 5: Load combined data into database
    load_lovac_fil_data(combined_data, schema=schema, table_name=table_name)

    logger.info(
        f"LOVAC FIL import flow completed successfully. Total rows loaded: {len(combined_data)}"
    )

    # Step 6: Create centroid geometry column
    create_centroid_geometry(schema=schema, table_name=table_name)

    # Step 7: Create lovac_fil_parcelle table
    create_lovac_fil_parcelle_table(
        schema=schema,
        dst_table_name="lovac_fil_parcelle",
        lovac_fil_table_name=table_name,
        parcelle_table_name="parcellaire",
        recreate=True,
    )

    return {
        "fields_processed": len(files),
        "total_rows": len(combined_data),
        "schema": schema,
        "table_name": table_name,
    }

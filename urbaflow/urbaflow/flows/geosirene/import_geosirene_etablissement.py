# %%
import pandas as pd
import numpy as np

from prefect import flow, task
from sqlalchemy import DDL, text

from urbaflow.urbaflow.shared_tasks.db_engine import create_engine
from urbaflow.logging_config import logger

# Fichier de géolocalisation des établissements réalisé par data.gouv.fr
# https://files.data.gouv.fr/geo-sirene/last/dep/
# https://files.data.gouv.fr/geo-sirene/last/dep/geo_siret_88.csv.gz

# Fichier StockEtablissement non géolocalisé
# (établissements actifs et fermés dans leur état courant au répertoire)
# https://files.data.gouv.fr/insee-sirene/StockEtablissement_utf8.zip

# Fichier de géolocalisation des établissements réalisé par l'INSEE
# base peu fiable concernant la geoloc
# "https://files.data.gouv.fr/insee-sirene-geo/GeolocalisationEtablissement_Sirene_pour_etudes_statistiques_utf8.zip"


def make_geosirene_url_for_dept(dep: str) -> str:
    """
    Return the URL of the geosirene data for the given department.
    Resource: https://www.data.gouv.fr/fr/datasets/base-sirene-des-etablissements-siret-geolocalisee-avec-la-base-dadresse-nationale-ban/
    """
    # "https://files.data.gouv.fr/geo-sirene/last/dep/geo_siret_88.csv.gz"
    return f"https://files.data.gouv.fr/geo-sirene/last/dep/geo_siret_{dep}.csv.gz"


@task
def extract_geosirene_etablissements(url) -> pd.DataFrame:
    """
    Download the geosirene data from the given URL and extract it with gzip to the data/geosirene folder.
    """
    return pd.read_csv(url, compression="gzip")


@task
def transform_before_load_geosirene_etablissement(data: pd.DataFrame, dep: str):
    column_mapping = {
        "siren": "siren",
        "nic": "nic",
        "siret": "siret",
        "statutDiffusionEtablissement": "statut_diffusion_etablissement",
        "dateCreationEtablissement": "date_creation_etablissement",
        "trancheEffectifsEtablissement": "tranche_effectifs_etablissement",
        "anneeEffectifsEtablissement": "annee_effectifs_etablissement",
        "activitePrincipaleRegistreMetiersEtablissement": "activite_principale_registre_metiers_etablissement",
        "dateDernierTraitementEtablissement": "date_dernier_traitement_etablissement",
        "etablissementSiege": "etablissement_siege",
        "nombrePeriodesEtablissement": "nombre_periodes_etablissement",
        "complementAdresseEtablissement": "complement_adresse_etablissement",
        "numeroVoieEtablissement": "numero_voie_etablissement",
        "indiceRepetitionEtablissement": "indice_repetition_etablissement",
        "dernierNumeroVoieEtablissement": "dernier_numero_voie_etablissement",
        "indiceRepetitionDernierNumeroVoieEtablissement": "indice_repetition_dernier_numero_voie_etablissement",
        "typeVoieEtablissement": "type_voie_etablissement",
        "libelleVoieEtablissement": "libelle_voie_etablissement",
        "codePostalEtablissement": "code_postal_etablissement",
        "libelleCommuneEtablissement": "libelle_commune_etablissement",
        "libelleCommuneEtrangerEtablissement": "libelle_commune_etranger_etablissement",
        "distributionSpecialeEtablissement": "distribution_speciale_etablissement",
        "codeCommuneEtablissement": "code_commune_etablissement",
        "codeCedexEtablissement": "code_cedex_etablissement",
        "libelleCedexEtablissement": "libelle_cedex_etablissement",
        "codePaysEtrangerEtablissement": "code_pays_etranger_etablissement",
        "libellePaysEtrangerEtablissement": "libelle_pays_etranger_etablissement",
        "identifiantAdresseEtablissement": "identifiant_adresse_etablissement",
        "coordonneeLambertAbscisseEtablissement": "coordonnee_lambert_abscisse_etablissement",
        "coordonneeLambertOrdonneeEtablissement": "coordonnee_lambert_ordonnee_etablissement",
        "complementAdresse2Etablissement": "complement_adresse2_etablissement",
        "numeroVoie2Etablissement": "numero_voie2_etablissement",
        "indiceRepetition2Etablissement": "indice_repetition2_etablissement",
        "typeVoie2Etablissement": "type_voie2_etablissement",
        "libelleVoie2Etablissement": "libelle_voie2_etablissement",
        "codePostal2Etablissement": "code_postal2_etablissement",
        "libelleCommune2Etablissement": "libelle_commune2_etablissement",
        "libelleCommuneEtranger2Etablissement": "libelle_commune_etranger2_etablissement",
        "distributionSpeciale2Etablissement": "distribution_speciale2_etablissement",
        "codeCommune2Etablissement": "code_commune2_etablissement",
        "codeCedex2Etablissement": "code_cedex2_etablissement",
        "libelleCedex2Etablissement": "libelle_cedex2_etablissement",
        "codePaysEtranger2Etablissement": "code_pays_etranger2_etablissement",
        "libellePaysEtranger2Etablissement": "libelle_pays_etranger2_etablissement",
        "dateDebut": "date_debut",
        "etatAdministratifEtablissement": "etat_administratif_etablissement",
        "enseigne1Etablissement": "enseigne1_etablissement",
        "enseigne2Etablissement": "enseigne2_etablissement",
        "enseigne3Etablissement": "enseigne3_etablissement",
        "denominationUsuelleEtablissement": "denomination_usuelle_etablissement",
        "activitePrincipaleEtablissement": "activite_principale_etablissement",
        "nomenclatureActivitePrincipaleEtablissement": "nomenclature_activite_principale_etablissement",
        "caractereEmployeurEtablissement": "caractere_employeur_etablissement",
        "longitude": "longitude",
        "latitude": "latitude",
        "geo_score": "geo_score",
        "geo_type": "geo_type",
        "geo_adresse": "geo_adresse",
        "geo_id": "geo_id",
        "geo_ligne": "geo_ligne",
        "geo_l4": "geo_l4",
        "geo_l5": "geo_l5",
    }
    data.rename(columns=column_mapping, inplace=True)
    columns_to_clean = [
        "complement_adresse_etablissement",
        "numero_voie_etablissement",
        "indice_repetition_etablissement",
        "dernier_numero_voie_etablissement",
        "indice_repetition_dernier_numero_voie_etablissement",
        "type_voie_etablissement",
        "libelle_voie_etablissement",
        "code_postal_etablissement",
        "distribution_speciale_etablissement",
        "code_cedex_etablissement",
        "libelle_cedex_etablissement",
        "identifiant_adresse_etablissement",
        "coordonnee_lambert_abscisse_etablissement",
        "coordonnee_lambert_ordonnee_etablissement",
        "numero_voie2_etablissement",
        "indice_repetition2_etablissement",
        "type_voie2_etablissement",
        "libelle_voie2_etablissement",
        "code_postal2_etablissement",
        "distribution_speciale2_etablissement",
        "libelle_cedex2_etablissement",
        "enseigne1_etablissement",
        "enseigne2_etablissement",
        "enseigne3_etablissement",
        "denomination_usuelle_etablissement",
    ]
    data[columns_to_clean] = data[columns_to_clean].replace("[ND]", np.nan)
    data["urbaflow_departement"] = dep
    data["urbaflow_inserted_at"] = pd.Timestamp.now()
    return data


@task
def create_geosirene_etablissement_table():
    e = create_engine()
    with e.begin() as conn:
        conn.execute(
            DDL(
                """
                DROP TABLE IF EXISTS geosirene_etablissement;
                CREATE TABLE geosirene_etablissement (
                    siren text,
                    nic text,
                    siret text PRIMARY KEY,
                    statut_diffusion_etablissement text,
                    date_creation_etablissement DATE,
                    tranche_effectifs_etablissement text,
                    annee_effectifs_etablissement INTEGER,
                    activite_principale_registre_metiers_etablissement text,
                    date_dernier_traitement_etablissement DATE,
                    etablissement_siege text,
                    nombre_periodes_etablissement INTEGER,
                    complement_adresse_etablissement text,
                    numero_voie_etablissement text,
                    indice_repetition_etablissement text,
                    dernier_numero_voie_etablissement text,
                    indice_repetition_dernier_numero_voie_etablissement text,
                    type_voie_etablissement text,
                    libelle_voie_etablissement text,
                    code_postal_etablissement text,
                    libelle_commune_etablissement text,
                    libelle_commune_etranger_etablissement text,
                    distribution_speciale_etablissement text,
                    code_commune_etablissement text,
                    code_cedex_etablissement text,
                    libelle_cedex_etablissement text,
                    code_pays_etranger_etablissement text,
                    libelle_pays_etranger_etablissement text,
                    identifiant_adresse_etablissement text,
                    coordonnee_lambert_abscisse_etablissement DOUBLE PRECISION,
                    coordonnee_lambert_ordonnee_etablissement DOUBLE PRECISION,
                    complement_adresse2_etablissement text,
                    numero_voie2_etablissement text,
                    indice_repetition2_etablissement text,
                    type_voie2_etablissement text,
                    libelle_voie2_etablissement text,
                    code_postal2_etablissement text,
                    libelle_commune2_etablissement text,
                    libelle_commune_etranger2_etablissement text,
                    distribution_speciale2_etablissement text,
                    code_commune2_etablissement text,
                    code_cedex2_etablissement text,
                    libelle_cedex2_etablissement text,
                    code_pays_etranger2_etablissement text,
                    libelle_pays_etranger2_etablissement text,
                    date_debut DATE,
                    etat_administratif_etablissement text,
                    enseigne1_etablissement text,
                    enseigne2_etablissement text,
                    enseigne3_etablissement text,
                    denomination_usuelle_etablissement text,
                    activite_principale_etablissement text,
                    nomenclature_activite_principale_etablissement text,
                    caractere_employeur_etablissement text,
                    longitude DOUBLE PRECISION,
                    latitude DOUBLE PRECISION,
                    geo_score DOUBLE PRECISION,
                    geo_type text,
                    geo_adresse text,
                    geo_id text,
                    geo_ligne text,
                    geo_l4 text,
                    geo_l5 text,
                    urbaflow_departement text,
                    urbaflow_inserted_at TIMESTAMP
                );
                """
            )
        )


@task
def delete_geosirene_etablissement_for_dep(dep: str):
    e = create_engine()
    with e.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM geosirene_etablissement WHERE urbaflow_departement = :dep;
                """
            ),
            {"dep": dep},
        )


@task
def load_geosirene_etablissement(data: pd.DataFrame):
    e = create_engine()
    chunk_size = 10000
    logger.info(
        f"Loading geosirene data to database. {len(data)} rows, {- (-len(data) // chunk_size)+1} chunks"
    )
    data.to_sql(
        "geosirene_etablissement",
        con=e,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=chunk_size,
    )


@task
def transform_after_load_geosirene_etablissement():
    """
    Add geometry to geosirene_etablissement table
    """
    e = create_engine()
    with e.begin() as conn:
        conn.execute(
            DDL(
                """
                ALTER TABLE public.geosirene_etablissement
                ADD COLUMN IF NOT EXISTS geom geometry(POINT, 2154);
                CREATE INDEX IF NOT EXISTS sidx_geosirene_etablissement_geom ON public.geosirene_etablissement USING GIST (geom);
                """
            )
        )
        logger.info("Added geom column to geosirene_etablissement table")
        conn.execute(
            text(
                """
                UPDATE public.geosirene_etablissement
                SET geom = st_transform(st_setsrid(st_makepoint(longitude, latitude), 4326), 2154)
                WHERE longitude IS NOT NULL AND latitude IS NOT NULL;
                """
            )
        )
        logger.info(
            "Updated geom column in locomvac table from parcellaire_france table"
        )
    return


@flow
def import_geosirene_data(dep: str, recreate_table: bool = True):
    if recreate_table:
        create_geosirene_etablissement_table()
    logger.info(f"Importing geosirene data for department {dep}")
    url = make_geosirene_url_for_dept(dep)
    logger.info(f"Downloading geosirene data from {url}")
    data = extract_geosirene_etablissements(url=url)
    data = transform_before_load_geosirene_etablissement(data, dep)
    delete_geosirene_etablissement_for_dep(dep)
    logger.info(data)
    load_geosirene_etablissement(data)
    transform_after_load_geosirene_etablissement()


# %%

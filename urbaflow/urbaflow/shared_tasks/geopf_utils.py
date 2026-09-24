"""
Utilitaires communs aux flux d'import de données de l'IGN distribuées par la
Géoplateforme (https://data.geopf.fr/telechargement).

Ce module centralise :
- la résolution d'un périmètre d'import (département, EPCI ou liste de communes)
  via l'API Découpage administratif (geo.api.gouv.fr),
- la recherche d'une archive de livraison sur le flux ATOM de téléchargement
  de la Géoplateforme.

Il est utilisé par les flux BD TOPO® et OCS GE, dont les livraisons sont toutes
deux organisées par zone départementale sur la Géoplateforme.
"""

import xml.etree.ElementTree as ElementTree
from typing import NamedTuple

import requests
from prefect import task
from shared_tasks.logging_config import get_logger

logger = get_logger(__name__)

# API de téléchargement de la Géoplateforme IGN
# https://data.geopf.fr/telechargement/capabilities
GEOPF_TELECHARGEMENT_URL = "https://data.geopf.fr/telechargement/resource"

# API Découpage administratif (Etalab)
GEO_API_COMMUNES_URL = "https://geo.api.gouv.fr/communes"

ATOM_NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "gpf_dl": "https://data.geopf.fr/annexes/ressources/xsd/gpf_dl.xsd",
}


class Perimeter(NamedTuple):
    """
    Périmètre d'import.

    Attributes:
        departments: codes des départements à télécharger.
        insee_codes: codes INSEE des communes à conserver. Si None, l'intégralité
            des départements est importée.
    """

    departments: tuple[str, ...]
    insee_codes: tuple[str, ...] | None


class GeopfResource(NamedTuple):
    """Archive départementale disponible au téléchargement sur la Géoplateforme."""

    name: str
    edition_date: str
    download_url: str


def normalize_department_code(code: str) -> str:
    """
    Normalise un code de département ('1' -> '01', '2a' -> '2A', '974' -> '974').
    """
    normalized = str(code).strip().upper()
    if not normalized:
        raise ValueError("Le code de département ne peut pas être vide.")
    if len(normalized) == 1:
        return f"0{normalized}"
    return normalized


def normalize_insee_code(code: str) -> str:
    """
    Normalise un code INSEE de commune sur 5 caractères ('1001' -> '01001').
    """
    normalized = str(code).strip().upper()
    if not normalized:
        raise ValueError("Le code INSEE ne peut pas être vide.")
    return normalized.zfill(5)


def department_from_insee_code(insee_code: str) -> str:
    """
    Déduit le code du département à partir d'un code INSEE de commune.

    Gère les cas particuliers de la Corse ('2A', '2B') et des départements
    et régions d'outre-mer (codes sur 3 chiffres).
    """
    normalized = normalize_insee_code(insee_code)
    if normalized.startswith(("2A", "2B")):
        return normalized[:2]
    if normalized.startswith(("97", "98")):
        return normalized[:3]
    return normalized[:2]


def geopf_zone_code(department: str) -> str:
    """
    Convertit un code de département en code de zone Géoplateforme ('35' -> 'D035').
    """
    return f"D{normalize_department_code(department).zfill(3)}"


def split_codes(codes: str | list[str] | None) -> tuple[str, ...]:
    """
    Découpe une liste de codes fournie en ligne de commande (séparés par des
    virgules ou des espaces) en un tuple de codes.
    """
    if not codes:
        return ()
    if isinstance(codes, str):
        codes = codes.replace(";", ",").replace(" ", ",").split(",")
    return tuple(code.strip() for code in codes if str(code).strip())


@task
def fetch_epci_communes(siren_epci: str) -> list[dict]:
    """
    Récupère les communes d'un EPCI via l'API Découpage administratif.
    """
    siren_epci = str(siren_epci).strip()
    response = requests.get(
        GEO_API_COMMUNES_URL,
        params={"codeEpci": siren_epci, "fields": "code,nom,codeDepartement"},
        timeout=30,
    )
    response.raise_for_status()
    communes = response.json()
    if not communes:
        raise ValueError(
            f"Aucune commune trouvée pour l'EPCI de SIREN {siren_epci}. "
            "Vérifier le numéro SIREN fourni."
        )
    logger.info("EPCI %s : %d commune(s) trouvée(s)", siren_epci, len(communes))
    return communes


def resolve_perimeter(
    departements: str | None = None,
    epci: str | None = None,
    communes: str | None = None,
) -> Perimeter:
    """
    Détermine le périmètre d'import à partir des options de la ligne de commande.

    Exactement une des trois options doit être renseignée.
    """
    provided_options = [option for option in (departements, epci, communes) if option]
    if len(provided_options) != 1:
        raise ValueError(
            "Un seul périmètre doit être fourni : --departement, --epci ou --communes."
        )

    if departements:
        department_codes = tuple(
            dict.fromkeys(
                normalize_department_code(code) for code in split_codes(departements)
            )
        )
        logger.info("Périmètre : département(s) %s", ", ".join(department_codes))
        return Perimeter(departments=department_codes, insee_codes=None)

    if epci:
        epci_communes = fetch_epci_communes(epci)
        insee_codes = tuple(
            dict.fromkeys(
                normalize_insee_code(commune["code"]) for commune in epci_communes
            )
        )
    else:
        insee_codes = tuple(
            dict.fromkeys(normalize_insee_code(code) for code in split_codes(communes))
        )

    department_codes = tuple(
        dict.fromkeys(department_from_insee_code(code) for code in insee_codes)
    )
    logger.info(
        "Périmètre : %d commune(s) sur le(s) département(s) %s",
        len(insee_codes),
        ", ".join(department_codes),
    )
    return Perimeter(departments=department_codes, insee_codes=insee_codes)


def insee_codes_of_department(perimeter: Perimeter, department: str) -> tuple[str, ...]:
    """
    Retourne les codes INSEE du périmètre appartenant au département donné.
    """
    if perimeter.insee_codes is None:
        return ()
    return tuple(
        code
        for code in perimeter.insee_codes
        if department_from_insee_code(code) == department
    )


def iter_atom_entries(url: str, params: dict) -> list[ElementTree.Element]:
    """
    Parcourt l'ensemble des pages d'un flux ATOM de la Géoplateforme et retourne
    les entrées rencontrées.
    """
    entries: list[ElementTree.Element] = []
    page = 1
    while True:
        response = requests.get(url, params={**params, "page": page}, timeout=60)
        response.raise_for_status()
        feed = ElementTree.fromstring(response.content)
        entries.extend(feed.findall("atom:entry", ATOM_NAMESPACES))
        page_count = int(
            feed.attrib.get(f"{{{ATOM_NAMESPACES['gpf_dl']}}}pagecount", "1")
        )
        if page >= page_count:
            return entries
        page += 1


def _find_archive_download_url(resource_url: str, resource_name: str) -> str:
    """
    Retourne l'URL de l'archive .7z correspondant à une livraison de la Géoplateforme.
    """
    response = requests.get(f"{resource_url}/{resource_name}", timeout=60)
    response.raise_for_status()
    feed = ElementTree.fromstring(response.content)

    for entry in feed.findall("atom:entry", ATOM_NAMESPACES):
        for link in entry.findall("atom:link", ATOM_NAMESPACES):
            href = link.attrib.get("href", "")
            if href.endswith(".7z"):
                return href
    raise ValueError(f"Aucun lien de téléchargement trouvé pour {resource_name}")


def find_geopf_resource(
    resource_id: str,
    zone: str,
    archive_format: str,
    edition_date: str | None = None,
    exclude_name_substring: str | None = None,
) -> GeopfResource:
    """
    Recherche une archive de livraison sur la Géoplateforme pour une zone et un
    format donnés.

    Args:
        resource_id: identifiant de la ressource Géoplateforme (ex: 'BDTOPO', 'OCSGE').
        zone: code de zone Géoplateforme (ex: 'D035').
        archive_format: format de livraison recherché (ex: 'GPKG').
        edition_date: millésime souhaité ('2026-06-15'). Si None, la dernière
            édition disponible est retenue.
        exclude_name_substring: si fourni, les livraisons dont le nom contient
            cette sous-chaîne sont ignorées (utile pour exclure les livraisons
            différentielles).

    Returns:
        GeopfResource: la livraison retenue, avec son URL de téléchargement.
    """
    resource_url = f"{GEOPF_TELECHARGEMENT_URL}/{resource_id}"
    entries = iter_atom_entries(resource_url, {"zone": zone, "format": archive_format})

    editions = [
        (
            entry.findtext("atom:title", default="", namespaces=ATOM_NAMESPACES),
            entry.findtext(
                "gpf_dl:editionDate", default="", namespaces=ATOM_NAMESPACES
            ),
        )
        for entry in entries
        if entry.findtext("gpf_dl:editionDate", namespaces=ATOM_NAMESPACES)
    ]
    if exclude_name_substring:
        editions = [
            edition for edition in editions if exclude_name_substring not in edition[0]
        ]
    if not editions:
        raise ValueError(
            f"Aucune archive {resource_id} {archive_format} disponible "
            f"pour la zone {zone}."
        )

    if edition_date:
        matching = [edition for edition in editions if edition[1] == edition_date]
        if not matching:
            available = ", ".join(sorted(edition[1] for edition in editions))
            raise ValueError(
                f"Millésime {edition_date} indisponible pour la zone {zone}. "
                f"Millésimes disponibles : {available}"
            )
        name, selected_edition_date = matching[0]
    else:
        name, selected_edition_date = max(editions, key=lambda edition: edition[1])

    download_url = _find_archive_download_url(resource_url, name)
    logger.info("Archive %s retenue pour la zone %s : %s", resource_id, zone, name)
    return GeopfResource(
        name=name, edition_date=selected_edition_date, download_url=download_url
    )

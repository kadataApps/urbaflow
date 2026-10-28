from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
from flows.docurba.import_docurba_documents import (
    build_documents_urbanisme,
    fetch_docurba_communes,
    get_departement_from_insee,
)

UPDATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_communes(codes: list[str]) -> pd.DataFrame:
    """Construit un DataFrame de communes BANATIC de test."""
    return pd.DataFrame(
        {
            "code_insee": codes,
            "nom_commune": [f"Commune {code}" for code in codes],
            "siren_epci": "200000001",
            "nom_epci": "CC de Test",
        }
    )


def make_docurba_row(code_insee: str, **values) -> dict:
    """Construit une ligne Docurba de test (colonnes vides par défaut)."""
    columns = [
        "pa_type_document",
        "pa_date_approbation",
        "pa_date_executoire",
        "pa_docurba_id",
        "pc_type_document",
        "pc_type_procedure",
        "pc_date_prescription",
        "pc_docurba_id",
        "plan_libelle_code_etat_complet",
        "cp_nom",
    ]
    return {"code_insee": code_insee, **dict.fromkeys(columns, ""), **values}


def test_get_departement_from_insee() -> None:
    """Vérifie la déduction du département, y compris outre-mer et Corse."""
    assert get_departement_from_insee("01001") == "01"
    assert get_departement_from_insee("2A004") == "2A"
    assert get_departement_from_insee("97411") == "974"
    assert get_departement_from_insee("1001") == "01"


def test_build_documents_with_heterogeneous_documents() -> None:
    """Vérifie les lignes communales et la synthèse EPCI hétérogène."""
    df_communes = make_communes(["01001", "01002", "01003", "01004"])
    df_docurba = pd.DataFrame(
        [
            make_docurba_row(
                "01001",
                pa_type_document="PLU",
                pa_date_approbation="2010-02-09",
                pa_docurba_id="a",
                cp_nom="Commune 01001",
            ),
            make_docurba_row(
                "01002",
                pa_type_document="CC",
                pa_date_approbation="2015-05-01",
                pa_docurba_id="b",
                pc_type_document="PLU",
                pc_type_procedure="Elaboration",
                pc_date_prescription="2023-03-01",
                pc_docurba_id="c",
            ),
            make_docurba_row("01003", plan_libelle_code_etat_complet="RNU"),
        ]
    )

    df = build_documents_urbanisme(df_communes, df_docurba, UPDATED_AT)

    assert list(df["type_territoire"]) == ["EPCI", "COM", "COM", "COM", "COM"]
    communes = df.set_index("code_territoire")
    assert communes.loc["01001", "document_opposable"] == "PLU"
    assert communes.loc["01001", "date_approbation"] == date(2010, 2, 9)
    assert communes.loc["01001", "document_en_cours"] is None
    assert communes.loc["01002", "document_opposable"] == "Carte communale"
    assert communes.loc["01002", "document_en_cours"] == "PLU"
    assert communes.loc["01002", "date_prescription_en_cours"] == date(2023, 3, 1)
    assert communes.loc["01003", "document_opposable"] == "RNU"
    assert communes.loc["01003", "date_approbation"] is None
    # Commune absente de Docurba : état inconnu
    assert communes.loc["01004", "document_opposable"] is None

    epci = communes.loc["200000001"]
    assert epci["nb_communes"] == 4
    assert epci["document_opposable"] == "Carte communale / PLU / RNU"
    assert epci["date_approbation"] is None
    assert epci["document_en_cours"] == "PLU"
    assert epci["date_prescription_en_cours"] is None
    assert (
        epci["repartition_documents_opposables"]
        == "Carte communale : 1, PLU : 1, RNU : 1"
    )


def test_build_documents_with_plui_covering_epci() -> None:
    """Vérifie que la ligne EPCI reprend le PLUi couvrant toutes les communes."""
    df_communes = make_communes(["35001", "35002"])
    plui = {
        "pa_type_document": "PLUiH",
        "pa_date_approbation": "2020-12-17",
        "pa_date_executoire": "2021-01-10",
        "pa_docurba_id": "plui",
        "pc_type_document": "PLUiH",
        "pc_type_procedure": "Révision",
        "pc_date_prescription": "2024-06-01",
        "pc_docurba_id": "revision",
        "cp_nom": "CC de Test",
    }
    df_docurba = pd.DataFrame(
        [make_docurba_row("35001", **plui), make_docurba_row("35002", **plui)]
    )

    epci = build_documents_urbanisme(df_communes, df_docurba, UPDATED_AT).iloc[0]

    assert epci["document_opposable"] == "PLUiH"
    assert epci["date_approbation"] == date(2020, 12, 17)
    assert epci["date_executoire"] == date(2021, 1, 10)
    assert epci["document_en_cours"] == "PLUiH"
    assert epci["type_procedure_en_cours"] == "Révision"
    assert epci["date_prescription_en_cours"] == date(2024, 6, 1)
    assert epci["collectivite_porteuse"] == "CC de Test"
    assert epci["repartition_documents_opposables"] == "PLUiH : 2"


def test_fetch_docurba_communes_reads_csv() -> None:
    """Vérifie l'appel à l'API Docurba et la lecture du CSV."""
    response = MagicMock()
    response.content = b'"code_insee","pa_type_document"\n"01001","PLU"\n"01002",""\n'
    with patch(
        "flows.docurba.import_docurba_documents.requests.get", return_value=response
    ) as mock_get:
        df = fetch_docurba_communes.fn("01", "2026-01-01")

    mock_get.assert_called_once()
    assert mock_get.call_args.kwargs["params"] == {
        "departement": "01",
        "avant": "2026-01-01",
    }
    assert df.to_dict("records") == [
        {"code_insee": "01001", "pa_type_document": "PLU"},
        {"code_insee": "01002", "pa_type_document": ""},
    ]

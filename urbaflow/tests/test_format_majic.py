import importlib.util
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, call, patch


class FormatMajicTests(unittest.TestCase):
    """Vérifie les dépendances et l'ordre des scripts de formatage MAJIC."""

    def setUp(self):
        """Charge le module avec des services simulés, sans connexion à la base."""
        self.sql_directory = Path("/temp/sql")
        self.connection = Mock()
        self.engine = Mock()
        self.engine.begin.return_value.__enter__ = Mock(
            return_value=self.connection
        )
        self.engine.begin.return_value.__exit__ = Mock(return_value=False)
        self.run_sql_script = Mock()
        self.replace_parameters = Mock()
        module_attributes = {
            "shared_tasks.config": {"TEMP_DIR": self.sql_directory.parent},
            "shared_tasks.db_engine": {
                "create_engine": Mock(return_value=self.engine)
            },
            "shared_tasks.db_sql_utils": {
                "run_sql_script": self.run_sql_script
            },
            "shared_tasks.logging_config": {"get_logger": Mock(return_value=Mock())},
            "shared_tasks.sql_query_utils": {
                "replace_parameters_in_script": self.replace_parameters
            },
        }
        dependency_modules = {}
        for module_name, attributes in module_attributes.items():
            dependency_module = ModuleType(module_name)
            dependency_module.__dict__.update(attributes)
            dependency_modules[module_name] = dependency_module

        module_path = (
            Path(__file__).resolve().parents[1]
            / "urbaflow/flows/cadastre/tasks/format_majic.py"
        )
        module_spec = importlib.util.spec_from_file_location(
            "format_majic", module_path
        )
        self.format_majic = importlib.util.module_from_spec(module_spec)
        with patch.dict("sys.modules", dependency_modules):
            module_spec.loader.exec_module(self.format_majic)

    def test_manual_correspondence_runs_before_owner_qualification(self):
        """Exécute la correspondance avant la qualification, sans initialisation."""
        self.format_majic.execute_format_majic_scripts()

        expected_scripts = [
            "2019/majic3_formatage_donnees.sql",
            "traitements/majic/0-renommage_tables.sql",
            "table_corresponance_manuelle_proprietaires.sql",
            "traitements/majic/1-traitement_qualification_proprietaires.sql",
            "traitements/majic/2-traitement_local_pev.sql",
            "traitements/majic/3-traitement_lots.sql",
            "traitements/majic/4-traitement_suf.sql",
            "traitements/majic/5-proprietaire_local10_update_gdprop.sql",
        ]
        self.assertEqual(
            self.run_sql_script.call_args_list,
            [
                call(
                    sql_filepath=self.sql_directory / script,
                    connection=self.connection,
                )
                for script in expected_scripts
            ],
        )
        self.assertEqual(
            self.replace_parameters.call_args_list,
            [
                call(
                    self.sql_directory / script,
                    {"[ANNEE]": "2019", "[LOT]": ""},
                )
                for script in expected_scripts
            ],
        )

    def test_initialization_only_runs_business_table_scripts(self):
        """Conserve l'initialisation des tables métiers et des nomenclatures."""
        self.format_majic.init_db_for_majic_import()

        self.assertEqual(
            self.run_sql_script.call_args_list,
            [
                call(
                    sql_filepath=self.sql_directory / script,
                    connection=self.connection,
                )
                for script in [
                    "commun_create_metier.sql",
                    "commun_insert_nomenclature.sql",
                ]
            ],
        )

    def test_correspondence_failure_stops_qualification(self):
        """Interrompt le formatage si le script de correspondance échoue."""
        self.run_sql_script.side_effect = [
            None,
            None,
            RuntimeError("Échec du chargement des correspondances"),
        ]

        with self.assertRaisesRegex(RuntimeError, "Échec du chargement"):
            self.format_majic.execute_format_majic_scripts()

        self.assertEqual(self.run_sql_script.call_count, 3)
        self.engine.begin.return_value.__exit__.assert_called_once()
        self.assertIs(
            self.engine.begin.return_value.__exit__.call_args.args[0],
            RuntimeError,
        )

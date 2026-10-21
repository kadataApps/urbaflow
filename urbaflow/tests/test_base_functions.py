from unittest.mock import MagicMock, patch

import pytest
from flows.base_functions import install_base_functions_flow
from shared_tasks.config import QUERIES_DIR


def test_install_base_functions_executes_complete_scripts() -> None:
    """Vérifie que les deux scripts complets utilisent la même transaction."""
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    cursor = connection.connection.cursor.return_value

    with patch("flows.base_functions.create_engine", return_value=engine):
        install_base_functions_flow.fn()

    expected_scripts = [
        (QUERIES_DIR / "base_functions" / script_name).read_text()
        for script_name in (
            "PolygonalMakeValid.sql",
            "PolygonalIntersection.sql",
        )
    ]
    assert [call.args[0] for call in cursor.execute.call_args_list] == (
        expected_scripts
    )
    engine.begin.assert_called_once_with()
    engine.begin.return_value.__exit__.assert_called_once_with(None, None, None)
    engine.dispose.assert_called_once_with()


@pytest.mark.parametrize("failed_script_index", [0, 1])
def test_install_base_functions_propagates_database_error(
    failed_script_index: int,
) -> None:
    """Vérifie qu'une erreur SQL interrompt la transaction et reste visible."""
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    error = RuntimeError("Erreur SQL de test")
    cursor = connection.connection.cursor.return_value
    cursor.execute.side_effect = [None] * failed_script_index + [error]

    with (
        patch("flows.base_functions.create_engine", return_value=engine),
        pytest.raises(RuntimeError, match="Erreur SQL de test"),
    ):
        install_base_functions_flow.fn()

    assert cursor.execute.call_count == failed_script_index + 1
    transaction_exit = engine.begin.return_value.__exit__.call_args
    assert transaction_exit.args[0] is RuntimeError
    assert transaction_exit.args[1] is error
    engine.dispose.assert_called_once_with()

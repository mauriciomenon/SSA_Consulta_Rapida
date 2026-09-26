import logging

import pytest

from utils.remote_itaipu import map_to_dataframe


@pytest.mark.parametrize("error", [OSError("leitura falhou"), RuntimeError("iterador falhou")])
def test_map_to_dataframe_preserves_failure_result_for_broken_iterable(error, caplog):
    caplog.set_level(logging.WARNING)
    def items():
        yield {"SSANumber": "202500001"}
        raise error

    assert map_to_dataframe(items()) is None
    assert "Falha ao mapear resposta para DataFrame" in caplog.text
    assert str(error) in caplog.text

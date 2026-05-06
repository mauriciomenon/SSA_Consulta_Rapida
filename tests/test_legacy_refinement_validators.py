from __future__ import annotations

import tests.historico_otimizacoes_cli as historico_cli
import tests.historico_otimizacoes_execucao as historico_execucao
import tests.teste_simples_refinamentos as refinamentos_simples


def test_refinement_simple_validator_rejects_partial_success(monkeypatch):
    monkeypatch.setattr(refinamentos_simples, "teste_cache_operacoes", lambda: True)
    monkeypatch.setattr(refinamentos_simples, "teste_configuracoes_json", lambda: True)
    monkeypatch.setattr(refinamentos_simples, "teste_estrutura_arquivos", lambda: False)
    monkeypatch.setattr(refinamentos_simples, "teste_hash_tracking", lambda: True)

    assert refinamentos_simples.main() is False


def test_execution_optimization_file_is_historical_note():
    assert historico_execucao.main() is True


def test_cli_optimization_file_is_historical_note():
    assert historico_cli.main() is True

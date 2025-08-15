# SSA_Consulta_Rapida

Ferramenta para consulta rápida de SSAs com CLI e GUI em Python.

## Requisitos
- Python 3.13+
- Windows (testado) ou compatível com PyQt6

## Instalação
```pwsh
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Uso
- CLI (padrão):
```pwsh
python main.py
```
- GUI:
```pwsh
python main.py --gui
```
- Reset do banco (antes da importação):
```pwsh
python main.py --reset-db file   # recria o arquivo do DB via schema
# ou
python main.py --reset-db table  # limpa apenas a tabela ssas
```

Notas sobre importação e versões:
- Arquivos mais novos (pela data no nome) prevalecem sobre dados antigos.
- Em empate/sem data, desempata por avanço de situação (sequência ASE → ADI → APL → APG → SPG → SEE → SAD → STE).

## Regras de exibição (CLI/GUI)
- Numero SSA com 9 dígitos (prefixo ano para <=5 dígitos; zfill para outros casos)
- Datas: somente data (sem horário)
- Semanas: sem sufixo ".0"
- Valores nulos: não exibir "nan/NaT/None"

Extras do CLI:
- Destaque de termos da última busca (negrito ANSI quando suportado). Defina NO_COLOR=1 (ou SSA_NO_COLOR=1) para desativar.
- Larguras fixas: Executor=6, Emissor=6, Semana programada=8, Status=5
- Filtros negativos: prefixe com ! ou - para excluir termos (ex.: MEL4,!cancelada)

## GUI – desempenho e previsibilidade
- Modelo leve (QAbstractTableModel) para renderização eficiente.
- Filtro com debounce (~350ms) e opção "Aplicar automaticamente" (desligado por padrão para não filtrar a cada tecla).
- Colunas ordenadas por `config/column_priority.json` (priority_order) e limitadas à largura da janela; use "Mostrar colunas extras" para revelar todas.
- Menu no cabeçalho para selecionar colunas (persistência via QSettings). Splitter vertical redimensionável com painel de detalhes.
- Cabeçalhos usam `short_labels` quando disponíveis.
- Duplo-clique abre um diálogo com detalhes formatados.

## Importação – robustez
- Arquivos sem coluna obrigatória (ex.: `numero_ssa`) são ignorados com log.
- `KeyboardInterrupt` (Ctrl+C) cancela a importação com rollback seguro.

## Hooks de Git (bloqueio de arquivos grandes)
- Pre-commit (arquivo > 99MB): `scripts/pre-commit-size-check.ps1`
- Pre-push (objetos >= 99MB no histórico): `scripts/pre-push-large-object-check.ps1`

Ative com um comando:
```pwsh
pwsh -NoProfile -File scripts/setup-git-hooks.ps1
```

## Testes
```pwsh
pytest -q
```

## Notas
- Consulte `docs_saida/CHANGELOG_IMPLEMENTACOES.md` para arquitetura, prioridades, labels e decisões.

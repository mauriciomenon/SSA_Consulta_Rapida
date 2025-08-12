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

## Regras de exibição (CLI/GUI)
- Numero SSA com 9 dígitos (prefixo ano para <=5 dígitos; zfill para outros casos)
- Datas: somente data (sem horário)
- Semanas: sem sufixo ".0"
- Valores nulos: não exibir "nan/NaT/None"

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

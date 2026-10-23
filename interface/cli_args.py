from __future__ import annotations

import argparse


class SafeRawTextHelpFormatter(argparse.RawTextHelpFormatter):
    """RawTextHelpFormatter que tolera % literais nos textos."""

    def _expand_help(self, action):
        help_text = action.help
        if help_text is None:
            return None
        try:
            return super()._expand_help(action)
        except (KeyError, ValueError):
            return help_text


def build_argument_parser(app_version: str, prog_name: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog_name,
        description=f"Consulta Rapida de SSAs v{app_version}",
        formatter_class=SafeRawTextHelpFormatter,
        epilog="""
EXEMPLOS DE USO
  Modo padrao:        python main.py
  Interface grafica:  python main.py --gui
  Reset de banco:     python main.py --reset-db
  Limpeza de dados:   python main.py --clean-data
  Reimportar tudo:    python main.py --force-rescan

Mais detalhes: README.md e docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md
""",
    )

    parser.add_argument(
        "--version", action="store_true", help="Exibe versao curta e encerra"
    )
    parser.add_argument(
        "--runtime-home",
        action="store_true",
        help="Usa a pasta de dados do usuario no executavel empacotado",
    )
    parser.add_argument(
        "--force-rescan",
        "--rescan",
        dest="force_rescan",
        action="store_true",
        help="""Reanalise completa: recria o banco com as planilhas de docs_entrada.

         --force-rescan e --rescan tem o mesmo efeito.

        COMPORTAMENTO:
         Ignora o cache de importacao (data/file_cache*.json)
         Monta um banco novo so com as planilhas presentes na pasta
         SSAs de planilhas retiradas da pasta deixam de existir no banco
         O banco anterior fica em data/ssas.db.full_rescan_backup_<data_hora>
         Para so acrescentar planilhas novas use "Atualizar dados" na GUI

        EXEMPLO: python main.py --force-rescan""",
    )
    parser.add_argument(
        "--skip-import",
        action="store_true",
        help="""Flag legada de compatibilidade.

        A importacao inicial automatica esta desativada por padrao.
        Para importar manualmente:
          - GUI: use o botao "Reescanear" (quando disponivel)
          - CLI: use --force-rescan/--rescan
        """,
    )
    parser.add_argument(
        "--optimized",
        action="store_true",
        help="""Sem efeito: o upsert em lote ja e o padrao do --force-rescan no main.py.""",
    )
    parser.add_argument(
        "--standard",
        action="store_true",
        help="""No --force-rescan do main.py, usa o upsert padrao (o mesmo da GUI e do
        executavel) no lugar do upsert em lote. O banco final e o mesmo; a
        diferenca de tempo medida e pequena.

        EXEMPLO: python main.py --standard --force-rescan""",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="""Inicia a interface grafica (GUI) em vez da CLI.

        RECURSOS DA GUI:
         Interface visual amigavel com PyQt6
         Filtros em tempo real com debounce
         Exibicao em tabela com ordenacao por colunas
         Protecao contra multiplas instancias
         Tooltips explicativos nos controles

        Exemplo: python main.py --gui""",
    )
    parser.add_argument(
        "--streamlit",
        "--web",
        dest="launch_streamlit",
        action="store_true",
        help="""Inicia a interface web (Streamlit) em segundo plano.

        CARACTERISTICAS:
         Interface moderna acessivel via navegador
         Filtros rapidos com sintaxe equivalente a CLI
         Indicadores resumidos e opcao de consulta a API

        Exemplo: python main.py --streamlit""",
    )
    parser.add_argument(
        "--streamlit-port",
        type=int,
        default=8501,
        help="Porta para a interface web (usar em conjunto com --streamlit)",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="""Zera o banco de dados e cria apenas a estrutura (sem importar dados).

        Operacao destrutiva:
         Backup automatico e criado antes da operacao
         Remove todos os dados existentes
         Recria estrutura limpa das tabelas
         Nao importa novos dados automaticamente

        Exemplo: python main.py --reset-db""",
    )
    parser.add_argument(
        "--clean-data",
        action="store_true",
        help="""Limpa backups e temporarios na pasta do banco de dados.

        LIMPEZA REALIZADA:
         Remove backups elegiveis com mais de 7 dias
         Remove temporarios elegiveis e organiza backups soltos
         Com SSA_DB_PATH, limita a limpeza a artefatos do banco escolhido
         Informa o espaco liberado pelos backups removidos

        Exemplo: python main.py --clean-data""",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Define o nivel de detalhe dos logs (padrao: INFO)",
    )
    parser.add_argument(
        "--acao",
        choices=["processar", "backfill"],
        default="processar",
        help="Define acao principal: processar (import normal) ou backfill (reprocessar diretorio historico).\n"
        "Uso para backfill com argumentos extras apos -- :\n"
        "  python main.py --acao backfill -- --dir docs_entrada --dry-run --smart-upsert\n",
    )
    return parser

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
  Modo otimizado:     python main.py --optimized
  Interface grafica:  python main.py --gui
  Reset de banco:     python main.py --reset-db
  Limpeza de dados:   python main.py --clean-data
  Reimportar tudo:    python main.py --force-rescan
  Otimizado + rescan: python main.py --optimized --force-rescan

Mais detalhes: README.md e GUIA_MODO_OPTIMIZED.md
""",
    )

    parser.add_argument(
        "--version", action="store_true", help="Exibe versao curta e encerra"
    )
    parser.add_argument(
        "--force-rescan",
        "--rescan",
        dest="force_rescan",
        action="store_true",
        help="""Reimporta todos os arquivos Excel ignorando o cache.

         DIFERENCAS
         --force-rescan: Nome atual, recomendado
         --rescan:       Alias para compatibilidade (mesmo efeito)


        COMPORTAMENTO:
         Ignora arquivo de controle de importacao (.last_import)
         Processa todos os arquivos Excel novamente
         Detecta e importa mudancas, adicoes e remocoes
         Util quando arquivos foram modificados manualmente

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
        help="""DEPRECATED: Modo otimizado agora e PADRAO. Use --standard para modo legado.

         AVISO: MODO OTIMIZADO JA E PADRAO
         Esta flag nao e mais necessaria - modo otimizado
         e ativado automaticamente para melhor performance.

         Use --standard se precisar do modo legado por
         compatibilidade ou debugging especifico.
        """,
    )
    parser.add_argument(
        "--standard",
        action="store_true",
        help="""Ativa modo LEGADO/DEBUG (mais lento, melhor para debugging).

         MODO LEGADO/DEBUG
         CARACTERISTICAS
            Operacoes linha por linha (mais lento)
            Logs mais detalhados para debugging
            Verificacoes adicionais de integridade
            Melhor para analise de problemas

         QUANDO USAR
            Debugging de problemas de importacao
            Analise detalhada de erros
            Compatibilidade com sistemas antigos
            Desenvolvimento e testes


        AVISO: Ate 90% mais lento que o modo padrao otimizado.

        EXEMPLOS:
        python main.py --standard
        python main.py --standard --force-rescan

        Mais detalhes: GUIA_MODO_OPTIMIZED.md""",
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
        help="""Limpa e sanitiza a pasta data (remove backups antigos).

        LIMPEZA REALIZADA:
         Remove backups mais antigos que 30 dias
         Organiza arquivos de log antigos
         Verifica integridade dos arquivos restantes
         Exibe relatorio de espaco liberado

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


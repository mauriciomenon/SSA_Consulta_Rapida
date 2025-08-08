# interface/command_handlers.py
"""
Handlers para comandos da interface de linha de comando.
"""

import logging
from exportacao.scheduled_exporter import ScheduledExporter

logger = logging.getLogger(__name__)

def handle_schedule_command(args):
    """
    Handler para o comando de gerenciamento de agendamentos.
    
    Args:
        args (list): Argumentos do comando.
    """
    if not args:
        print("Uso: -schedule <subcomando> [argumentos]")
        print("Subcomandos disponíveis:")
        print("  list                    - Lista todos os agendamentos")
        print("  add <nome> <frequencia> - Adiciona um novo agendamento")
        print("  remove <nome>           - Remove um agendamento")
        return
    
    subcommand = args[0]
    scheduled_exporter = ScheduledExporter()
    
    if subcommand == "list":
        schedules = scheduled_exporter.get_schedules()
        if not schedules:
            print("Nenhum agendamento configurado.")
            return
        
        print("Agendamentos configurados:")
        for name, config in schedules.items():
            print(f"  {name}:")
            print(f"    Frequência: {config.get('frequency', 'daily')}")
            print(f"    Última exportação: {config.get('last_export', 'Nunca')}")
            print(f"    Diretório de saída: {config.get('output_dir', 'docs_saida')}")
            print(f"    Nome base do arquivo: {config.get('base_filename', f'scheduled_export_{name}')}")
            if 'filters' in config:
                print(f"    Filtros: {config['filters']}")
            print()
    
    elif subcommand == "add":
        if len(args) < 3:
            print("Uso: -schedule add <nome> <frequencia>")
            return
        
        name = args[1]
        frequency = args[2]
        
        if frequency not in ["daily", "weekly", "monthly"]:
            print("Frequência inválida. Use: daily, weekly, ou monthly")
            return
        
        schedule_config = {
            "frequency": frequency,
            "output_dir": "docs_saida/scheduled",
            "base_filename": f"scheduled_export_{name}",
            "last_export": None
        }
        
        scheduled_exporter.add_schedule(name, schedule_config)
        print(f"Agendamento '{name}' adicionado com sucesso.")
    
    elif subcommand == "remove":
        if len(args) < 2:
            print("Uso: -schedule remove <nome>")
            return
        
        name = args[1]
        scheduled_exporter.remove_schedule(name)
        print(f"Agendamento '{name}' removido com sucesso.")
    
    else:
        print(f"Subcomando desconhecido: {subcommand}")
        print("Use -schedule sem argumentos para ver a ajuda.")
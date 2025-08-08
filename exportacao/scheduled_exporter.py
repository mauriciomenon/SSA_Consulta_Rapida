# exportacao/scheduled_exporter.py
"""
Módulo para exportação agendada de dados.
"""

import pandas as pd
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any
from exportacao.exporter import export_dataframe

logger = logging.getLogger(__name__)

class ScheduledExporter:
    """Classe para gerenciar exportações agendadas."""
    
    def __init__(self, config_file: str = "config/scheduled_exports.json"):
        self.config_file = config_file
        self.schedules = self._load_schedules()
    
    def _load_schedules(self) -> Dict[str, Any]:
        """Carrega as configurações de agendamento."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar configurações de agendamento: {e}")
                return {}
        return {}
    
    def _save_schedules(self):
        """Salva as configurações de agendamento."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.schedules, f, indent=4, ensure_ascii=False)
            logger.info("Configurações de agendamento salvas com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao salvar configurações de agendamento: {e}")
    
    def add_schedule(self, name: str, schedule_config: Dict[str, Any]):
        """
        Adiciona uma nova configuração de agendamento.
        
        Args:
            name (str): Nome do agendamento.
            schedule_config (Dict[str, Any]): Configuração do agendamento.
        """
        self.schedules[name] = schedule_config
        self._save_schedules()
        logger.info(f"Agendamento '{name}' adicionado com sucesso.")
    
    def remove_schedule(self, name: str):
        """
        Remove uma configuração de agendamento.
        
        Args:
            name (str): Nome do agendamento a ser removido.
        """
        if name in self.schedules:
            del self.schedules[name]
            self._save_schedules()
            logger.info(f"Agendamento '{name}' removido com sucesso.")
        else:
            logger.warning(f"Agendamento '{name}' não encontrado.")
    
    def get_schedules(self) -> Dict[str, Any]:
        """Retorna todas as configurações de agendamento."""
        return self.schedules
    
    def should_export(self, name: str) -> bool:
        """
        Verifica se é hora de exportar com base na configuração.
        
        Args:
            name (str): Nome do agendamento.
            
        Returns:
            bool: True se deve exportar, False caso contrário.
        """
        if name not in self.schedules:
            return False
        
        schedule = self.schedules[name]
        last_export = schedule.get('last_export')
        frequency = schedule.get('frequency', 'daily')  # daily, weekly, monthly
        
        if not last_export:
            return True
        
        try:
            last_export_dt = datetime.fromisoformat(last_export)
        except ValueError:
            logger.error(f"Formato de data inválido para o agendamento '{name}': {last_export}")
            return True
        
        now = datetime.now()
        
        if frequency == 'daily':
            next_export = last_export_dt + timedelta(days=1)
        elif frequency == 'weekly':
            next_export = last_export_dt + timedelta(weeks=1)
        elif frequency == 'monthly':
            next_export = last_export_dt + timedelta(days=30)  # Aproximação
        else:
            logger.warning(f"Frequência desconhecida para o agendamento '{name}': {frequency}")
            return True
        
        return now >= next_export
    
    def update_last_export(self, name: str):
        """
        Atualiza a data da última exportação.
        
        Args:
            name (str): Nome do agendamento.
        """
        if name in self.schedules:
            self.schedules[name]['last_export'] = datetime.now().isoformat()
            self._save_schedules()
    
    def run_scheduled_exports(self, df: pd.DataFrame, display_map: Dict[str, str]):
        """
        Executa as exportações agendadas que estão prontas.
        
        Args:
            df (pd.DataFrame): DataFrame com os dados a serem exportados.
            display_map (Dict[str, str]): Mapeamento de colunas para exibição.
        """
        for name, schedule in self.schedules.items():
            if self.should_export(name):
                try:
                    output_dir = schedule.get('output_dir', 'docs_saida')
                    base_filename = schedule.get('base_filename', f'scheduled_export_{name}')
                    
                    # Aplicar filtros, se houver
                    filtered_df = df.copy()
                    if 'filters' in schedule:
                        from core.app_logic import advanced_filter_dataframe
                        filtered_df = advanced_filter_dataframe(filtered_df, schedule['filters'])
                    
                    export_dataframe(filtered_df, base_filename, output_dir, display_map)
                    self.update_last_export(name)
                    logger.info(f"Exportação agendada '{name}' concluída com sucesso.")
                except Exception as e:
                    logger.error(f"Erro ao executar exportação agendada '{name}': {e}")
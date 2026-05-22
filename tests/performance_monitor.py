#!/usr/bin/env python3
"""
Monitor de Performance e Travamentos
===================================

Script para monitorar continuamente a performance da GUI e detectar travamentos.

Uso: python tests/performance_monitor.py
Data: 2025-08-18
"""

import os
import signal
import sys
import time
from datetime import datetime
from typing import Any, TypedDict

# Ajuste do sys.path deve ocorrer antes dos imports locais do projeto; permitido aqui.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtCore import QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from gui.gui_ssa import QT_AVAILABLE  # noqa: E402

SSAMainWindow: type[Any] | None
try:
    from gui.gui_ssa import SSAMainWindow as _GuiSSAMainWindow

    SSAMainWindow = _GuiSSAMainWindow
except Exception:
    # Se não conseguir importar a GUI principal, marcamos como indisponível
    SSAMainWindow = None
    QT_AVAILABLE = False


class MonitorStats(TypedDict):
    filtros_testados: int
    tempo_total: float
    tempo_max: float
    tempo_min: float
    travamentos_detectados: int
    inicio: datetime


class PerformanceMonitor:
    """Monitor de performance para detectar travamentos."""

    def __init__(self):
        window_cls = SSAMainWindow
        if not QT_AVAILABLE or window_cls is None:
            raise RuntimeError("Qt/GUI principal não disponível para monitor")
        self.app = QApplication([])
        self.window = window_cls()
        self.running = True
        self.stats: MonitorStats = {
            "filtros_testados": 0,
            "tempo_total": 0.0,
            "tempo_max": 0.0,
            "tempo_min": float("inf"),
            "travamentos_detectados": 0,
            "inicio": datetime.now(),
        }

        # Lista de filtros para testar
        self.test_filters = [
            "svp",
            "mel3",
            "mel4",
            "pendente",
            "executada",
            "em execução",
            "g076",
            "g077",
            "cancelada",
            "amp",
            "programar",
            "planejamento",
            "ie3",
            "ie4",
            "sv1",
            "sv2",
            "!",
            "mel,svp",
            "pendente,programar",
        ]

        self.current_filter_index = 0

        # Timer para testes automáticos
        self.timer = QTimer()
        self.timer.timeout.connect(self.run_filter_test)

        # Configuração do sinal para parada limpa
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, _signum, _frame):
        """Handler para parada limpa do programa."""
        print("\n\n Parando monitor...")
        self.stop_monitoring()

    def start_monitoring(self, interval_ms=5000):
        """Inicia o monitoramento."""
        print("START Iniciando Monitor de Performance da GUI SSA PoC")
        print("=" * 60)
        print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Intervalo de teste: {interval_ms / 1000:.1f}s")
        print(f"Filtros a testar: {len(self.test_filters)}")
        print("Pressione Ctrl+C para parar...")
        print("=" * 60)

        self.window.show()

        # Aguarda carregamento inicial
        QApplication.processEvents()
        time.sleep(2)

        # Inicia testes automáticos
        self.timer.start(interval_ms)

        # Executa aplicação
        try:
            self.app.exec()
        except KeyboardInterrupt:
            pass
        finally:
            self.print_final_stats()

    def run_filter_test(self):
        """Executa um teste de filtro."""
        if not self.running or self.current_filter_index >= len(self.test_filters):
            self.current_filter_index = 0  # Reinicia o ciclo

        filter_text = self.test_filters[self.current_filter_index]

        print(
            f"INFO Testando filtro #{self.stats['filtros_testados'] + 1}: '{filter_text}'",
            end=" ",
        )

        start_time = time.time()

        try:
            # Aplica o filtro
            self.window.search_input.setText(filter_text)
            self.window.filter_data()

            # Permite processamento
            QApplication.processEvents()

            end_time = time.time()
            duration = end_time - start_time

            # Atualiza estatísticas
            self.stats["filtros_testados"] += 1
            self.stats["tempo_total"] += duration
            self.stats["tempo_max"] = max(self.stats["tempo_max"], duration)
            self.stats["tempo_min"] = min(self.stats["tempo_min"], duration)

            # Detecta possível travamento
            if duration > 3.0:
                self.stats["travamentos_detectados"] += 1
                print(f"WARN  TRAVAMENTO DETECTADO! ({duration:.2f}s)")
                self.log_issue(filter_text, duration, "TRAVAMENTO")
            elif duration > 1.0:
                print(f"PERF Lento ({duration:.2f}s)")
                self.log_issue(filter_text, duration, "LENTO")
            else:
                print(f"OK OK ({duration:.3f}s)")

        except Exception as e:
            print(f"ERR ERRO: {e}")
            self.log_issue(filter_text, 0, f"ERRO: {e}")

        self.current_filter_index += 1

        # Mostra estatísticas a cada 10 testes
        if self.stats["filtros_testados"] % 10 == 0:
            self.print_stats()

    def log_issue(self, filter_text, duration, issue_type):
        """Registra problemas detectados."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} | {issue_type} | Filtro: '{filter_text}' | Tempo: {duration:.3f}s"

        # Salva em arquivo de log
        with open(
            os.path.join(project_root, "logs", "performance_issues.log"),
            "a",
            encoding="utf-8",
        ) as f:
            f.write(log_entry + "\n")

    def print_stats(self):
        """Imprime estatísticas atuais."""
        if self.stats["filtros_testados"] == 0:
            return

        tempo_medio = self.stats["tempo_total"] / self.stats["filtros_testados"]
        tempo_decorrido = (datetime.now() - self.stats["inicio"]).total_seconds()

        print("\n" + "-" * 50)
        print("INFO ESTATÍSTICAS ATUAIS")
        print(f"   Filtros testados: {self.stats['filtros_testados']}")
        print(f"   Tempo médio: {tempo_medio:.3f}s")
        print(f"   Tempo mínimo: {self.stats['tempo_min']:.3f}s")
        print(f"   Tempo máximo: {self.stats['tempo_max']:.3f}s")
        print(f"   Travamentos: {self.stats['travamentos_detectados']}")
        print(f"   Tempo decorrido: {tempo_decorrido / 60:.1f} min")
        print("-" * 50 + "\n")

    def print_final_stats(self):
        """Imprime estatísticas finais."""
        print("\n" + "=" * 60)
        print("STAT RELATÓRIO FINAL DE PERFORMANCE")
        print("=" * 60)

        if self.stats["filtros_testados"] == 0:
            print("ERR Nenhum teste foi executado.")
            return

        tempo_medio = self.stats["tempo_total"] / self.stats["filtros_testados"]
        tempo_decorrido = (datetime.now() - self.stats["inicio"]).total_seconds()

        print("INFO Resumo dos Testes:")
        print(f"   • Total de filtros testados: {self.stats['filtros_testados']}")
        print(f"   • Tempo médio de resposta: {tempo_medio:.3f}s")
        print(f"   • Tempo mínimo: {self.stats['tempo_min']:.3f}s")
        print(f"   • Tempo máximo: {self.stats['tempo_max']:.3f}s")
        print(f"   • Travamentos detectados: {self.stats['travamentos_detectados']}")
        print(
            f"   • Taxa de travamento: {(self.stats['travamentos_detectados'] / self.stats['filtros_testados'] * 100):.1f}%"
        )
        print(f"   • Tempo total de monitoramento: {tempo_decorrido / 60:.1f} min")

        print("\nDONE Avaliação de Performance:")
        if tempo_medio < 0.5:
            print("   OK EXCELENTE - Resposta muito rápida")
        elif tempo_medio < 1.0:
            print("   OK BOA - Resposta aceitável")
        elif tempo_medio < 2.0:
            print("   WARN  REGULAR - Resposta lenta")
        else:
            print("   ERR RUIM - Resposta muito lenta")

        if self.stats["travamentos_detectados"] == 0:
            print("   OK ESTÁVEL - Nenhum travamento detectado")
        elif self.stats["travamentos_detectados"] < 3:
            print("   WARN  INSTÁVEL - Poucos travamentos detectados")
        else:
            print("   ERR MUITO INSTÁVEL - Muitos travamentos detectados")

        print("\nTIP Recomendações:")
        if tempo_medio > 1.0:
            print("   • Otimizar algoritmos de filtro")
            print("   • Implementar cache para buscas frequentes")
        if self.stats["travamentos_detectados"] > 0:
            print("   • Investigar filtros que causam travamentos")
            print("   • Adicionar timeout nos filtros")
        if self.stats["tempo_max"] > 5.0:
            print("   • Implementar limitação de resultados mais rigorosa")

        print("=" * 60)

    def stop_monitoring(self):
        """Para o monitoramento."""
        self.running = False
        if self.timer.isActive():
            self.timer.stop()
        self.app.quit()


def main():
    """Função principal."""
    # Cria diretório de logs se não existir
    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Inicia o monitor
    monitor = PerformanceMonitor()

    # Permite configurar intervalo via argumento
    interval = 3000  # 3 segundos por padrão
    if len(sys.argv) > 1:
        try:
            interval = int(sys.argv[1]) * 1000
        except ValueError:
            print("WARN  Intervalo inválido, usando 3 segundos")

    monitor.start_monitoring(interval)


if __name__ == "__main__":
    main()

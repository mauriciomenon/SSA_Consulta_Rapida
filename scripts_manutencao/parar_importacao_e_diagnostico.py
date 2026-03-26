#!/usr/bin/env python3
# parar_importacao_e_diagnostico.py
"""
Script para parar importação lenta e fazer diagnóstico rápido.
"""

import importlib
import os
import sqlite3
import time
from typing import Any

psutil: Any | None
try:
    psutil = importlib.import_module("psutil")
except Exception:
    psutil = None


def _require_psutil() -> Any:
    if psutil is None:
        raise RuntimeError(
            "Dependencia opcional ausente: instale psutil para executar este script"
        )
    return psutil


def find_and_kill_python_processes():
    """Encontra e para processos Python relacionados à importação."""
    psutil_mod = _require_psutil()
    print("INFO Procurando processos Python em execução...")

    current_pid = os.getpid()
    killed_processes = []

    for proc in psutil_mod.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.info["name"] and "python" in proc.info["name"].lower():
                if proc.info["pid"] != current_pid:  # Não matar a si mesmo
                    cmdline = " ".join(proc.info["cmdline"] or [])

                    # Verificar se é processo relacionado ao SSA
                    if any(
                        keyword in cmdline.lower()
                        for keyword in [
                            "main.py",
                            "import",
                            "test_import",
                            "ssa",
                            "excel",
                        ]
                    ):
                        print(
                            f"  DONE Encontrado processo relacionado: PID {proc.info['pid']}"
                        )
                        print(f"     Comando: {cmdline[:100]}...")

                        try:
                            proc.terminate()  # Terminar gentilmente
                            proc.wait(timeout=5)  # Esperar 5 segundos
                            killed_processes.append(proc.info["pid"])
                            print(f"  OK Processo {proc.info['pid']} terminado")
                        except (psutil_mod.NoSuchProcess, psutil_mod.TimeoutExpired):
                            try:
                                proc.kill()  # Forçar se necessário
                                killed_processes.append(proc.info["pid"])
                                print(
                                    f"  PERF Processo {proc.info['pid']} forçado a parar"
                                )
                            except psutil_mod.NoSuchProcess:
                                print(
                                    f"  WARN  Processo {proc.info['pid']} já finalizou"
                                )
                        except psutil_mod.AccessDenied:
                            print(
                                f"  ERR Sem permissão para parar processo {proc.info['pid']}"
                            )

        except (
            psutil_mod.NoSuchProcess,
            psutil_mod.AccessDenied,
            psutil_mod.ZombieProcess,
        ) as exc:
            print(
                f"  WARN Falha ao acessar processo: {getattr(proc, 'pid', '?')} ({exc})"
            )
            continue

    if not killed_processes:
        print("  INFO Nenhum processo Python relacionado ao SSA encontrado")
    else:
        print(f"  OK Parados {len(killed_processes)} processos")

    return killed_processes


def check_database_status():
    """Verifica o status atual do banco de dados."""
    print("\nINFO VERIFICANDO STATUS DO BANCO DE DADOS")
    print("-" * 40)

    db_path = "data/ssas.db"

    if not os.path.exists(db_path):
        print("ERR Banco de dados não encontrado!")
        return False

    try:
        # Verificar se o banco está acessível
        with sqlite3.connect(db_path, timeout=1) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM ssas")
            total_records = cursor.fetchone()[0]
            print(f"OK Banco acessível: {total_records} registros")

            # Verificar últimas modificações
            cursor = conn.execute("""
                SELECT data_cadastro, COUNT(*)
                FROM ssas
                WHERE data_cadastro IS NOT NULL
                GROUP BY data_cadastro
                ORDER BY data_cadastro DESC
                LIMIT 3
            """)
            recent_dates = cursor.fetchall()

            if recent_dates:
                print(" Dados mais recentes:")
                for date, count in recent_dates:
                    print(f"   {date}: {count} registros")

            return True

    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            print(" Banco de dados TRAVADO - processo de importação ainda ativo")
            return False
        else:
            print(f"ERR Erro ao acessar banco: {e}")
            return False
    except Exception as e:
        print(f"ERR Erro inesperado: {e}")
        return False


def check_system_resources():
    """Verifica recursos do sistema."""
    psutil_mod = _require_psutil()
    print("\nINFO  RECURSOS DO SISTEMA")
    print("-" * 25)

    # CPU
    cpu_percent = psutil_mod.cpu_percent(interval=1)
    print(f" CPU: {cpu_percent}%")

    # Memória
    memory = psutil_mod.virtual_memory()
    print(
        f" RAM: {memory.percent}% usado ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)"
    )

    # Disco
    disk = psutil_mod.disk_usage(".")
    print(f" Disco: {disk.percent}% usado ({disk.free // (1024**3):.1f}GB livres)")

    # Processos Python
    python_procs = []
    for proc in psutil_mod.process_iter(
        ["pid", "name", "cpu_percent", "memory_percent"]
    ):
        try:
            if proc.info["name"] and "python" in proc.info["name"].lower():
                python_procs.append(
                    {
                        "pid": proc.info["pid"],
                        "cpu": proc.info["cpu_percent"] or 0,
                        "memory": proc.info["memory_percent"] or 0,
                    }
                )
        except (psutil_mod.NoSuchProcess, psutil_mod.AccessDenied):
            continue

    if python_procs:
        print(f" Processos Python ativos: {len(python_procs)}")
        for proc in python_procs[:3]:  # Top 3
            print(
                f"   PID {proc['pid']}: CPU {proc['cpu']:.1f}%, RAM {proc['memory']:.1f}%"
            )


def run_diagnostico():
    """Executa o fluxo completo de diagnostico e recuperacao."""
    if psutil is None:
        print(
            "ERR Dependencia opcional ausente: instale psutil para executar este script"
        )
        return

    print(" PARAR IMPORTAÇÃO LENTA E DIAGNÓSTICO RÁPIDO")
    print("=" * 50)
    print()

    # 1. Verificar recursos do sistema
    check_system_resources()

    # 2. Verificar status do banco
    db_accessible = check_database_status()

    # 3. Se banco travado, parar processos
    if not db_accessible:
        print("\n PARANDO PROCESSOS DE IMPORTAÇÃO")
        print("-" * 35)
        killed = find_and_kill_python_processes()

        if killed:
            print("\n⏳ Aguardando 3 segundos...")
            time.sleep(3)

            # Verificar novamente
            print("\nRUN VERIFICANDO NOVAMENTE O BANCO")
            print("-" * 32)
            db_accessible = check_database_status()

    # 4. Relatório final
    print("\n" + "=" * 50)
    print("INFO RESUMO DO DIAGNÓSTICO")
    print("-" * 24)

    if db_accessible:
        print("OK Banco de dados acessível")
        print("OK Importação não está mais bloqueando")
        print("\nSTART PRÓXIMOS PASSOS RECOMENDADOS:")
        print("   1. Execute: python otimizacao_importacao_rapida.py")
        print("   2. Ou use: python main.py --force-rescan")
        print("   3. Para uso normal: python main.py")
    else:
        print("ERR Banco ainda inacessível")
        print("WARN  Pode ser necessário reiniciar o terminal/VS Code")
        print("\n🆘 SOLUÇÕES DE EMERGÊNCIA:")
        print("   1. Feche todos os terminais Python")
        print("   2. Reinicie o VS Code")
        print("   3. Em último caso: reinicie o computador")

    print("\n Para importação rápida no futuro:")
    print("   Use sempre: python otimizacao_importacao_rapida.py")


def main():
    run_diagnostico()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n Interrompido pelo usuário")
    except Exception as e:
        print(f"\nERR Erro: {e}")

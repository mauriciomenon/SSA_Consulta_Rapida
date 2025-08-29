#!/usr/bin/env python3
# monitor_importacao.py
"""
Script para monitorar o progresso da importação em tempo real.
"""

import os
import sys
import time
import sqlite3
from datetime import datetime

def monitor_database_growth():
    """Monitora o crescimento do banco de dados em tempo real."""
    db_path = "data/ssas.db"
    
    if not os.path.exists(db_path):
        print("❌ Banco de dados não encontrado")
        return
    
    print("📊 MONITOR DE IMPORTAÇÃO EM TEMPO REAL")
    print("=" * 45)
    print("Pressione Ctrl+C para parar o monitoramento")
    print()
    
    last_count = 0
    start_time = time.time()
    
    try:
        while True:
            try:
                with sqlite3.connect(db_path, timeout=1) as conn:
                    # Contar registros totais
                    cursor = conn.execute("SELECT COUNT(*) FROM ssas")
                    current_count = cursor.fetchone()[0]
                    
                    # Calcular estatísticas
                    records_added = current_count - last_count
                    elapsed_time = time.time() - start_time
                    
                    if elapsed_time > 0:
                        rate = records_added / elapsed_time if elapsed_time > 0 else 0
                    else:
                        rate = 0
                    
                    # Mostrar status
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] 📊 Total: {current_count:,} registros | +{records_added} | Taxa: {rate:.1f} reg/s")
                    
                    last_count = current_count
                    
                    # Verificar últimas modificações
                    if records_added > 0:
                        cursor = conn.execute("""
                            SELECT data_cadastro, COUNT(*) 
                            FROM ssas 
                            WHERE data_cadastro IS NOT NULL 
                            GROUP BY data_cadastro 
                            ORDER BY data_cadastro DESC 
                            LIMIT 1
                        """)
                        recent = cursor.fetchone()
                        if recent:
                            print(f"         📅 Última data processada: {recent[0]} ({recent[1]} registros)")
                
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔒 Banco travado - importação ativa")
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Erro: {e}")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  Erro inesperado: {e}")
            
            time.sleep(2)  # Verificar a cada 2 segundos
            
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoramento interrompido pelo usuário")
        elapsed_time = time.time() - start_time
        print(f"⏱️  Tempo total monitorado: {elapsed_time:.1f}s")
        if last_count > 0:
            print(f"📊 Registros no final: {last_count:,}")

def show_quick_stats():
    """Mostra estatísticas rápidas do banco."""
    db_path = "data/ssas.db"
    
    if not os.path.exists(db_path):
        print("❌ Banco de dados não encontrado")
        return
    
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            print("📊 ESTATÍSTICAS RÁPIDAS DO BANCO")
            print("-" * 32)
            
            # Total de registros
            cursor = conn.execute("SELECT COUNT(*) FROM ssas")
            total = cursor.fetchone()[0]
            print(f"📈 Total de registros: {total:,}")
            
            # SSAs únicas
            cursor = conn.execute("SELECT COUNT(DISTINCT numero_ssa) FROM ssas WHERE numero_ssa IS NOT NULL")
            unique_ssas = cursor.fetchone()[0]
            print(f"🔢 SSAs únicas: {unique_ssas:,}")
            
            # Duplicatas
            if unique_ssas < total:
                duplicates = total - unique_ssas
                print(f"⚠️  Registros duplicados: {duplicates:,}")
            else:
                print("✅ Sem duplicatas detectadas")
            
            # Distribuição por situação
            cursor = conn.execute("""
                SELECT situacao, COUNT(*) 
                FROM ssas 
                WHERE situacao IS NOT NULL 
                GROUP BY situacao 
                ORDER BY COUNT(*) DESC 
                LIMIT 5
            """)
            situations = cursor.fetchall()
            
            if situations:
                print("\n📊 Top 5 situações:")
                for situation, count in situations:
                    percentage = (count / total) * 100
                    print(f"   {situation}: {count:,} ({percentage:.1f}%)")
            
            # Dados mais recentes
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
                print("\n📅 Datas mais recentes:")
                for date, count in recent_dates:
                    print(f"   {date}: {count:,} registros")
            
    except Exception as e:
        print(f"❌ Erro ao obter estatísticas: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        show_quick_stats()
    else:
        monitor_database_growth()

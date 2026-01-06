#!/usr/bin/env python3
import sqlite3
import shutil
from pathlib import Path

def limpar_banco():
    """Limpa completamente o banco de dados"""
    db_path = Path('data/ssas.db')
    backup_path = Path('data/ssas_backup_antes_limpeza_final.db')

    try:
        # Fazer backup se banco existir
        if db_path.exists():
            shutil.copy2(db_path, backup_path)
            print(f'OK Backup criado: {backup_path}')

        # Limpar tabela
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM ssas')
            count_before = cursor.fetchone()[0]
            print(f'INFO Registros antes da limpeza: {count_before:,}')

            cursor.execute('DELETE FROM ssas')
            cursor.execute('VACUUM')  # Otimizar o banco
            conn.commit()

            cursor.execute('SELECT COUNT(*) FROM ssas')
            count_after = cursor.fetchone()[0]
            print(f'INFO Registros após limpeza: {count_after:,}')
            print('OK Banco limpo com sucesso!')

    except Exception as e:
        print(f'ERR Erro ao limpar banco: {e}')
        return False

    return True

if __name__ == '__main__':
    limpar_banco()

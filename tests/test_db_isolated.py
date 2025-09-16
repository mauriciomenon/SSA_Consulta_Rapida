import os
import sqlite3
import shutil
import glob
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger("test")

def check_and_restore_database(db_path):
    """
    Verifica se o banco de dados está vazio ou corrompido e restaura um backup se necessário.
    """
    try:
        # Verifica se o arquivo existe e tem tamanho adequado
        if not os.path.exists(db_path):
            logger.warning(f"Banco de dados não encontrado: {db_path}")
            return _restore_database_from_backup(db_path)

        # Verifica tamanho do arquivo (considera vazio se < 32KB)
        file_size = os.path.getsize(db_path)
        if file_size < 32768:  # 32KB
            logger.warning(f"Banco de dados muito pequeno ({file_size} bytes), possivelmente corrompido")
            return _restore_database_from_backup(db_path)

        # Verifica se consegue conectar e se tem a tabela ssas
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='ssas'")
                if cursor.fetchone()[0] == 0:
                    logger.warning("Tabela 'ssas' não encontrada no banco de dados")
                    return _restore_database_from_backup(db_path)

                # Verifica se a tabela tem dados
                cursor.execute("SELECT COUNT(*) FROM ssas")
                row_count = cursor.fetchone()[0]
                if row_count == 0:
                    logger.warning("Banco de dados está vazio (0 registros)")
                    return _restore_database_from_backup(db_path)

                logger.info(f"Banco de dados válido: {file_size} bytes, {row_count} registros")
                return True

        except sqlite3.Error as e:
            logger.error(f"Erro ao verificar banco de dados: {e}")
            return _restore_database_from_backup(db_path)

    except Exception as e:
        logger.error(f"Erro na verificação do banco: {e}")
        return False

def _restore_database_from_backup(db_path):
    """
    Restaura o banco de dados a partir do melhor backup disponível.
    """
    try:
        project_root = os.path.dirname(os.path.dirname(db_path))
        backup_dir = os.path.join(project_root, 'data', 'historico_backups')

        if not os.path.exists(backup_dir):
            logger.error("Pasta de backups históricos não encontrada")
            return False

        # Lista todos os backups .db e ordena por tamanho (maiores primeiro)
        backup_files = glob.glob(os.path.join(backup_dir, '*.db'))
        if not backup_files:
            logger.error("Nenhum backup encontrado")
            return False

        # Ordena por tamanho decrescente para pegar o maior backup
        backup_files.sort(key=lambda x: os.path.getsize(x), reverse=True)

        for backup_file in backup_files:
            backup_size = os.path.getsize(backup_file)
            if backup_size < 32768:  # Ignora backups muito pequenos
                continue

            try:
                # Testa se o backup é válido
                with sqlite3.connect(backup_file) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='ssas'")
                    if cursor.fetchone()[0] == 0:
                        continue

                    cursor.execute("SELECT COUNT(*) FROM ssas")
                    row_count = cursor.fetchone()[0]
                    if row_count == 0:
                        continue

                # Backup é válido, restaura
                logger.info(f"Restaurando banco de {os.path.basename(backup_file)} ({backup_size} bytes, {row_count} registros)")

                # Faz backup do arquivo corrompido se existir
                if os.path.exists(db_path):
                    corrupted_backup = f"{db_path}.corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.move(db_path, corrupted_backup)
                    logger.info(f"Arquivo corrompido salvo como: {os.path.basename(corrupted_backup)}")

                # Copia o backup válido
                shutil.copy2(backup_file, db_path)
                logger.info("Banco de dados restaurado com sucesso")
                return True

            except sqlite3.Error:
                continue  # Tenta próximo backup

        logger.error("Nenhum backup válido encontrado")
        return False

    except Exception as e:
        logger.error(f"Erro ao restaurar backup: {e}")
        return False

if __name__ == "__main__":
    db_path = r'data\ssas.db'
    print(f'Testando verificação do banco: {db_path}')
    print(f'Tamanho atual: {os.path.getsize(db_path)} bytes')

    result = check_and_restore_database(db_path)
    print(f'Resultado da verificação: {result}')
    print(f'Tamanho após verificação: {os.path.getsize(db_path)} bytes')

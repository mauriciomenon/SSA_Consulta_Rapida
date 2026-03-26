"""
utils/file_metadata.py

Utilitários para extrair metadados de arquivos e interpretar datas em nomes
de relatórios como:
  "Consulta SSA - 14-07-2025_0343PM.xlsx"

Também fornece helpers para comparar arquivos por data (priorizando a data
parseada do nome; caso não encontrada, usa mtime do arquivo).
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import Iterable, Optional, Tuple

# Arquivos protegidos: nunca devem participar de lógica de "arquivo mais recente"
PROTECTED_FILENAMES = {
    "readme.md",
    "changelog_implementacoes.md",
    "column_priority.json",
    "display_mappings.json",
    "column_mappings.json",
}

DATE_NAME_REGEXES = [
    # e.g.: 14-07-2025_0343PM
    re.compile(
        r"(?P<d>\d{2})-(?P<m>\d{2})-(?P<y>\d{4})[_\- ](?P<h>\d{2})(?P<M>\d{2})(?P<ampm>AM|PM)",
        re.IGNORECASE,
    ),
    # e.g.: 14-07-2025 03:43 PM
    re.compile(
        r"(?P<d>\d{2})-(?P<m>\d{2})-(?P<y>\d{4})[ _](?P<h>\d{1,2}):(?P<M>\d{2})[ _]?(?P<ampm>AM|PM)",
        re.IGNORECASE,
    ),
    # e.g.: 2025-07-14 15.43
    re.compile(
        r"(?P<y>\d{4})[-_/](?P<m>\d{2})[-_/](?P<d>\d{2})[ T](?P<h>\d{1,2})[.:](?P<M>\d{2})",
        re.IGNORECASE,
    ),
]


def parse_datetime_from_filename(filename: str) -> Optional[datetime]:
    """Tenta extrair uma datetime a partir do nome do arquivo.

    Aceita padrões comuns usados nos relatórios SSA. Caso nenhum padrão
    seja identificado, retorna None.
    """
    base = os.path.basename(filename)
    for rx in DATE_NAME_REGEXES:
        m = rx.search(base)
        if not m:
            continue
        gd = m.groupdict()
        try:
            y = int(gd.get("y") or "0")
            mth = int(gd.get("m") or "0")
            d = int(gd.get("d") or "0")
            h = int(gd.get("h") or "0")
            M = int(gd.get("M") or "0")
            ampm = gd.get("ampm")
            if ampm:
                ampm = ampm.upper()
                # Converte 12h em 24h
                if ampm == "PM" and h != 12:
                    h += 12
                if ampm == "AM" and h == 12:
                    h = 0
            return datetime(y, mth, d, h, M)
        except Exception:
            # Se parsing falhar, tenta próximo padrão
            continue
    return None


def get_file_times(file_path: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Retorna (mtime, ctime) do arquivo se existirem; caso contrário, (None, None)."""
    try:
        stat = os.stat(file_path)
        mtime = datetime.fromtimestamp(stat.st_mtime)
        ctime = datetime.fromtimestamp(stat.st_ctime)
        return mtime, ctime
    except OSError:
        return None, None


def best_datetime_for_file(file_path: str) -> Optional[datetime]:
    """Escolhe a melhor datetime para um arquivo, priorizando a existente no nome.

    Se não houver data no nome, usa mtime; na falta, ctime; senão None.
    """
    by_name = parse_datetime_from_filename(file_path)
    if by_name:
        return by_name
    mtime, ctime = get_file_times(file_path)
    return mtime or ctime


def choose_latest(files: Iterable[str]) -> Optional[str]:
    """Dado um iterável de arquivos, retorna aquele com a data mais recente
    conforme best_datetime_for_file. Retorna None se vazio.
    """
    best: Optional[Tuple[datetime, str]] = None
    for f in files or []:
        # Ignora arquivos protegidos por nome
        try:
            base = os.path.basename(f).lower()
            if base in PROTECTED_FILENAMES:
                continue
        except Exception:
            pass
        dt = best_datetime_for_file(f)
        if dt is None:
            continue
        if best is None or dt > best[0]:
            best = (dt, f)
    return best[1] if best else None


logger = logging.getLogger(__name__)


def extract_datetime_from_filename(filename: str) -> Optional[datetime]:
    """
    Extrai data e hora do nome do arquivo Excel.

    Formatos suportados:
    - Todas as SSAs - 15-07-2025_0143PM (2).xlsx
    - IEE3_Emissor__202401_20250715_Todas as SSAs - 15-07-2025_1033AM.xlsx
    - SSAs Executadas_15-07-2025_0239PM.xlsx

    Args:
        filename (str): Nome do arquivo

    Returns:
        Optional[datetime]: Objeto datetime se conseguir extrair, None caso contrário
    """
    # Remove a extensão
    base_name = os.path.splitext(filename)[0]

    # Padrão regex para capturar dd-mm-YYYY_HHminminAM/PM
    # Exemplos: 15-07-2025_0143PM, 15-07-2025_1033AM
    pattern = r"(\d{2})-(\d{2})-(\d{4})_(\d{2})(\d{2})(AM|PM)"

    match = re.search(pattern, base_name)
    if match:
        day, month, year, hour, minute, ampm = match.groups()

        try:
            # Converte para inteiros
            day = int(day)
            month = int(month)
            year = int(year)
            hour = int(hour)
            minute = int(minute)

            # Converte formato 12h para 24h
            if ampm.upper() == "PM" and hour != 12:
                hour += 12
            elif ampm.upper() == "AM" and hour == 12:
                hour = 0

            # Cria o objeto datetime
            dt = datetime(year, month, day, hour, minute)
            logger.debug(f"Data extraída de '{filename}': {dt.isoformat()}")
            return dt

        except ValueError as e:
            logger.warning(f"Erro ao converter data do arquivo '{filename}': {e}")
            return None
    else:
        logger.warning(f"Formato de data não reconhecido no arquivo '{filename}'")
        return None


def get_file_metadata(file_path: str) -> Tuple[str, Optional[str], str]:
    """
    Extrai metadados completos do arquivo para controle de versões.

    Args:
        file_path (str): Caminho completo do arquivo

    Returns:
        Tuple[str, Optional[str], str]: (nome_arquivo, data_arquivo_iso, data_importacao_iso)
    """
    filename = os.path.basename(file_path)

    # Extrai data/hora do nome do arquivo
    file_datetime = extract_datetime_from_filename(filename)
    file_datetime_iso = file_datetime.isoformat() if file_datetime else None

    # Data/hora atual da importação
    import_datetime_iso = datetime.now().isoformat()

    logger.debug(
        f"Metadados do arquivo '{filename}': data_arquivo={file_datetime_iso}, data_importacao={import_datetime_iso}"
    )

    return filename, file_datetime_iso, import_datetime_iso


def should_update_ssa(
    existing_file_date: Optional[str], new_file_date: Optional[str]
) -> bool:
    """
    Determina se uma SSA deve ser atualizada baseado nas datas dos arquivos.

    Args:
        existing_file_date (Optional[str]): Data ISO do arquivo existente no DB
        new_file_date (Optional[str]): Data ISO do novo arquivo

    Returns:
        bool: True se deve atualizar, False caso contrário
    """
    # Se não temos data do arquivo existente, sempre atualiza
    if not existing_file_date:
        logger.debug("Arquivo existente sem data - atualizando")
        return True

    # Se não temos data do novo arquivo, não atualiza
    if not new_file_date:
        logger.debug("Novo arquivo sem data - não atualizando")
        return False

    try:
        existing_dt = datetime.fromisoformat(existing_file_date)
        new_dt = datetime.fromisoformat(new_file_date)

        should_update = new_dt > existing_dt
        logger.debug(
            f"Comparação de datas: existente={existing_dt}, novo={new_dt}, atualizar={should_update}"
        )
        return should_update

    except ValueError as e:
        logger.warning(f"Erro ao comparar datas: {e}")
        # Em caso de erro, atualiza por segurança
        return True


# Função para testar a extração de datas
def test_date_extraction():
    """Função de teste para validar a extração de datas."""
    test_files = [
        "Todas as SSAs - 15-07-2025_0143PM (2).xlsx",
        "IEE3_Emissor__202401_20250715_Todas as SSAs - 15-07-2025_1033AM.xlsx",
        "SSAs Executadas_15-07-2025_0239PM.xlsx",
        "Consulta SSA - 14-07-2025_0343PM.xlsx",
        "Pendentes de Execução_15-07-2025_0223PM.xlsx",
    ]

    print("=== Teste de Extração de Datas ===")
    for filename in test_files:
        dt = extract_datetime_from_filename(filename)
        print(f"{filename:<60} -> {dt.isoformat() if dt else 'FALHA'}")


if __name__ == "__main__":
    # Executa teste se chamado diretamente
    test_date_extraction()

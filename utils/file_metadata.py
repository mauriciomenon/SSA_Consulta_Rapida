"""
utils/file_metadata.py

Utilitários para extrair metadados de arquivos e interpretar datas em nomes
de relatórios como:
  "Consulta SSA - 14-07-2025_0343PM.xlsx"

A data de um arquivo prioriza a data parseada do nome; sem ela, usa mtime
(ou ctime) do arquivo.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

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
        except (TypeError, ValueError) as exc:
            logger.debug(
                "Falha ao interpretar data no nome %s com padrao %s: %s",
                base,
                rx.pattern,
                exc,
            )
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

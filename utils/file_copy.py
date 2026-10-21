"""File copy helpers for import/staging workflows."""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path


def copy_source_without_execute_bit(source: str, destination: Path) -> None:
    """Copy a regular file to a new destination (exclusive create, no execute bit).

    A failure after the destination was created removes it, so no partial copy
    is left behind; a destination that already existed is never touched.
    """
    with open(source, "rb") as source_handle:
        source_stat = os.fstat(source_handle.fileno())
        if not stat.S_ISREG(source_stat.st_mode):
            raise ValueError(f"Fonte nao e arquivo regular: {source}")
        created = False
        try:
            with open(destination, "xb") as destination_handle:
                created = True
                shutil.copyfileobj(source_handle, destination_handle)
            os.chmod(destination, source_stat.st_mode & ~0o111)
            os.utime(
                destination,
                ns=(source_stat.st_atime_ns, source_stat.st_mtime_ns),
            )
        except BaseException:
            if created and os.path.exists(destination):
                os.unlink(destination)
            raise

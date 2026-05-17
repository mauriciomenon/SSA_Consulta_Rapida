"""System and SAM integration helpers for the SSA GUI."""

from __future__ import annotations

import ntpath
import os
import posixpath
import shutil
import sys
from typing import Any

SAM_HOME_URL = "https://osprd.itaipu/SAM_SMA/"
SAM_SSA_PUBLIC_VIEW_URL = (
    "https://osprd.itaipu/SAM_SMA/SSAPublicView.aspx"
    "?SerialNumber={numero_ssa}&language=pt"
)
SAM_ALLOWED_URL_HOSTS = frozenset({"osprd.itaipu"})


def build_sam_ssa_url(numero_ssa: str) -> str:
    return SAM_SSA_PUBLIC_VIEW_URL.format(numero_ssa=str(numero_ssa).strip())


def open_allowed_url(
    url: str,
    *,
    qdesktopservices: Any,
    qurl_cls: Any,
    logger: Any,
) -> bool:
    safe_url = str(url or "").strip()
    if not safe_url:
        return False
    qurl = qurl_cls(safe_url)
    if not is_allowed_sam_url(qurl):
        logger.warning(
            "URL externa bloqueada por politica de seguranca: scheme=%s host=%s",
            str(qurl.scheme() or "").casefold() or "<empty>",
            str(qurl.host() or "").casefold() or "<empty>",
        )
        return False
    try:
        return bool(qdesktopservices.openUrl(qurl))
    except Exception as exc:
        logger.warning("Falha ao abrir URL externa %s: %s", safe_url, exc)
        return False


def is_allowed_sam_url(qurl: Any) -> bool:
    scheme = str(qurl.scheme() or "").casefold()
    host = str(qurl.host() or "").casefold()
    return scheme == "https" and host in SAM_ALLOWED_URL_HOSTS


def validate_local_open_target(
    target_path: str,
    *,
    must_exist: bool,
    expect_dir: bool | None,
    allowed_base: str | list[str] | tuple[str, ...] | None = None,
) -> str:
    if allowed_base is None:
        raise ValueError("Base permitida obrigatoria para caminho local.")
    raw = str(target_path or "")
    if not raw.strip():
        raise ValueError("Caminho vazio para abertura.")
    if any(ch in raw for ch in ("\x00", "\n", "\r")):
        raise ValueError("Caminho contem caracteres invalidos.")
    if _contains_command_metacharacter(raw):
        raise ValueError("Caminho contem caracteres reservados para comandos.")
    raw_parts = [part for part in raw.replace("\\", "/").split("/") if part]
    if ".." in raw_parts:
        raise ValueError("Caminho com parent traversal nao permitido.")
    normalized = os.path.realpath(os.path.normpath(raw))
    _validate_allowed_base(normalized, allowed_base)
    if os.path.basename(normalized).startswith("-"):
        raise ValueError(
            "Caminho inicia com '-' e pode ser interpretado como opcao de comando."
        )
    if must_exist and not os.path.exists(normalized):
        raise FileNotFoundError(f"Caminho nao encontrado: {normalized}")
    if expect_dir is True and os.path.exists(normalized) and not os.path.isdir(normalized):
        raise ValueError(f"Era esperado diretorio: {normalized}")
    if expect_dir is False and os.path.exists(normalized) and os.path.isdir(normalized):
        raise ValueError(f"Era esperado arquivo: {normalized}")
    return normalized


def _contains_command_metacharacter(raw_path: str) -> bool:
    return any(ch in raw_path for ch in (";", "&", "|", "`", "$", "<", ">"))


def _validate_allowed_base(
    normalized: str, allowed_base: str | list[str] | tuple[str, ...]
) -> None:
    raw_bases = [allowed_base] if isinstance(allowed_base, str) else list(allowed_base)
    for raw_base in raw_bases:
        normalized_base = os.path.realpath(os.path.normpath(str(raw_base)))
        try:
            common_path = os.path.commonpath([normalized, normalized_base])
        except ValueError:
            continue
        if common_path == normalized_base:
            return
    raise ValueError("Caminho fora da base permitida.")


def resolve_platform_open_command() -> str:
    preferred_paths: list[str] = []
    path_module = os.path
    if sys.platform.startswith("win"):
        windir = os.environ.get("WINDIR", r"C:\Windows")
        preferred_paths.append(ntpath.join(windir, "explorer.exe"))
        cmd = "explorer"
        path_module = ntpath
    elif sys.platform == "darwin":
        preferred_paths.append("/usr/bin/open")
        cmd = "open"
        path_module = posixpath
    else:
        preferred_paths.extend(("/usr/bin/xdg-open", "/bin/xdg-open"))
        cmd = "xdg-open"
        path_module = posixpath
    for preferred in preferred_paths:
        preferred_abs = path_module.abspath(preferred)
        if path_module.isabs(preferred_abs) and path_module.isfile(preferred_abs):
            return preferred_abs
    fallback = shutil.which(cmd)
    if fallback:
        fallback_abs = path_module.abspath(fallback)
        if path_module.isabs(fallback_abs) and path_module.isfile(fallback_abs):
            return fallback_abs
    raise RuntimeError(f"Comando indisponivel para abrir recurso: {cmd}")


def build_platform_open_args(command: str, target_path: str) -> list[str]:
    if sys.platform.startswith("win"):
        return [command, target_path]
    return [command, "--", target_path]

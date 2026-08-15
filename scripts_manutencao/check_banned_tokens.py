#!/usr/bin/env python3
"""Scan repository for banned tokens (security / governance guardrail).

Exit codes:
 0 - clean
 1 - violations found
 2 - internal error (script misconfiguration)

By default ignores:
 - Virtual environments / site-packages
 - Compiled artifacts (__pycache__)
 - Data export directories (docs_saida/, extracao/, exportacao/)
 - .git directory

Configuration via environment variables:
    BANNED_TOKENS: comma-separated tokens (default:
        OPENROUTER_API_KEY,openrouter,openai,anthropic,gpt-4,gpt-3.5)
    SCAN_INCLUDE_EXT: comma-separated file extensions (default:
        .py,.yml,.yaml,.md,.txt,.json,.toml,.ini,.sh,.ps1)
  SCAN_MAX_FILE_KB: max file size to scan (default: 512)

Safe to run in CI or pre-commit.
"""
from __future__ import annotations

import logging
import os
import re
from collections.abc import Iterable
from pathlib import Path

DEFAULT_TOKENS = [
    "OPENROUTER_API_KEY",
    "openrouter",
    "openai",
    "anthropic",
    # Removed overly broad 'model:' / 'models:' to reduce benign hits
    "gpt-4",
    "gpt-3.5",
]

DEFAULT_EXTS = [
    ".py",
    ".yml",
    ".yaml",
    ".md",
    ".txt",
    ".json",
    ".toml",
    ".ini",
    ".sh",
    ".ps1",
]

IGNORE_DIRS = {
    ".git",
    "__pycache__",
    "venv",
    "env",
    "build",
    "dist",
    "docs_saida",
    "extracao",
    "exportacao",
    "launchers/platforms",  # large vendor tree
    "launchers/platforms/macos_arm64/venv",  # nested venv
    "docs",  # documentation with historical references
}


# Files to exclude completely from scanning (self-reference problem)
IGNORE_FILES = {
    "check_banned_tokens.py",  # This file contains token definitions
    "SECRET_HISTORY_REPORT.md",  # Historical security audit
    "SESSION_CONTEXT_SNAPSHOT_20250915.md",  # Historical snapshot
}

ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"
ANSI_RESET = "\033[0m"


def load_tokens() -> list[str]:
    raw = os.environ.get("BANNED_TOKENS")
    if not raw:
        return DEFAULT_TOKENS
    return [t.strip() for t in raw.split(",") if t.strip()]


def load_exts() -> set[str]:
    raw = os.environ.get("SCAN_INCLUDE_EXT")
    if not raw:
        return set(DEFAULT_EXTS)
    return {e.strip() for e in raw.split(",") if e.strip()}


def should_skip(path: Path) -> bool:
    # Skip by directory
    parts = set(path.parts)
    if any(d in parts for d in IGNORE_DIRS):
        return True
    # Skip by filename
    if path.name in IGNORE_FILES:
        return True
    return False


SCAN_DIRS_DEFAULT = [
    "armazenamento",
    "core",
    "utils",
    "gui",
    "interface",
    "scripts_manutencao",
    "tests",
    "config",
    ".github",
]


def iter_candidate_files(root: Path, allowed_exts: set[str], max_kb: int) -> Iterable[Path]:
    scan_dirs_env = os.environ.get("SCAN_DIRS")
    if scan_dirs_env:
        base_dirs = [d.strip() for d in scan_dirs_env.split(",") if d.strip()]
    else:
        base_dirs = SCAN_DIRS_DEFAULT
    candidates: list[Path] = []
    for base in base_dirs:
        base_path = root / base
        if not base_path.exists():
            continue
        for p in base_path.rglob("*"):
            candidates.append(p)
    for p in candidates:
        if not p.is_file():
            continue
        if should_skip(p):
            continue
        if p.suffix.lower() not in allowed_exts:
            continue
        try:
            size_kb = p.stat().st_size / 1024
        except OSError:
            continue
        if size_kb > max_kb:
            continue
        yield p


ALLOWED_CONTEXT_REGEXES = [
    re.compile(r"Model:\s*[A-Z0-9_-]{2,}\\b", re.IGNORECASE),  # descriptive 'Model: GT802'
]


def is_allowed_line(line: str) -> bool:
    return any(rx.search(line) for rx in ALLOWED_CONTEXT_REGEXES)


def scan_file(path: Path, tokens: list[str]) -> list[tuple[int, str, str]]:
    findings: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:  # noqa: BLE001
        return [(0, "ERROR", f"{e}")]
    lowered = text.lower()
    for token in tokens:
        token_lower = token.lower()
        if token_lower in lowered:
            # Collect line snippets
            pattern = re.compile(re.escape(token_lower), re.IGNORECASE)
            for i, line in enumerate(text.splitlines(), start=1):
                if pattern.search(line) and not is_allowed_line(line):
                    findings.append((i, token, line.strip()))
    return findings


def main() -> int:
    tokens = load_tokens()
    allowed_exts = load_exts()
    max_kb = int(os.environ.get("SCAN_MAX_FILE_KB", "512"))
    root = Path(os.environ.get("SCAN_ROOT", Path.cwd()))

    violations = 0
    all_reports: list[str] = []

    candidate_files = list(iter_candidate_files(root, allowed_exts, max_kb))
    if not candidate_files:
        logging.info("Nenhum arquivo candidato encontrado. A varredura foi encerrada sem execucao.")
        return 0

    for file_path in candidate_files:
        hits = scan_file(file_path, tokens)
        if hits:
            for line_no, token, snippet in hits:
                violations += 1
                all_reports.append(f"{file_path}:{line_no}: token '{token}' -> {snippet[:200]}")

    if violations:
        logging.error("BANNED TOKEN SCAN FAILED — %d occurrence(s) found", violations)
        for r in all_reports:
            logging.error(r)
        logging.info("Adjust token list via BANNED_TOKENS env if false positive.")
        return 1

    logging.info("BANNED TOKEN SCAN CLEAN")
    return 0


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        raise SystemExit(main())
    except KeyboardInterrupt as exc:  # noqa: PERF203
        logging.warning("Interrupted")
        raise SystemExit(130) from exc

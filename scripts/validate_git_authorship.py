#!/usr/bin/env python3
"""Valida identidade humana e mensagens antes de commits e publicacoes Git."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

EMAILS = {
    "mauriciomenon@users.noreply.github.com",
    "54405514+mauriciomenon@users.noreply.github.com",
    "mauricio.menon@gmail.com",
}
IDENTITY = re.compile(r"(.+) <([^<>]+)> -?\d+ [+-]\d{4}")
TOOLS = r"(?:ai|ia|assistant|assistente|inteligencia artificial|artificial intelligence|claude|codex|chatgpt|openai|anthropic|copilot|cursor|qoder|gemini|grok|aider|opencode|devin)\b"
FORBIDDEN = re.compile(
    r"\b(?:co-authored-by|signed-off-by|generated-by)\s*:"
    r"|\bgenerated\s+with\b"
    r"|\b(?:generated|written|authored|co-authored|created|assisted)\s+(?:by|with)\s+(?:an?\s+)?[\[*`_]*"
    + TOOLS
    + r"|\b(?:gerado|escrito|criado|produzido|assistido)\s+(?:por|com)\s+(?:uma?\s+)?[\[*`_]*"
    + TOOLS
    + r"|\b(?:co-?author|coautoria|autoria|credits?|creditos?)\s*[:=-]?\s*"
    + TOOLS,
    re.IGNORECASE | re.MULTILINE,
)


def git(*args: str, data: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", *args],
        input=data,
        capture_output=True,
        check=False,
        timeout=60,
        env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1"},
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"git {args[0]} falhou: {detail}")
    return result.stdout


def normalize(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", value) if not unicodedata.combining(char)
    ).casefold()


def validate_identity(value: str, context: str) -> None:
    match = IDENTITY.fullmatch(value.strip())
    if not match:
        raise ValueError(f"{context}: identidade Git invalida")
    name, email = match.groups()
    if normalize(name) != "mauricio menon" or email.casefold() not in EMAILS:
        raise ValueError(f"{context}: identidade nao autorizada: {name} <{email}>")


def validate_message(message: str, context: str) -> None:
    if FORBIDDEN.search(normalize(message)):
        raise ValueError(f"{context}: texto de coautoria ou credito proibido")


def decode_text(content: bytes, encoding: str, context: str) -> str:
    try:
        return content.decode(encoding)
    except (LookupError, UnicodeError) as error:
        raise ValueError(f"{context}: texto ou encoding Git invalido: {encoding}") from error


def validate_metadata(content: bytes, kind: str, oid: str) -> bytes | None:
    headers, separator, message = content.partition(b"\n\n")
    if not separator:
        raise ValueError(f"{oid}: objeto {kind} sem mensagem separada")
    fields: dict[bytes, list[bytes]] = {}
    for line in headers.splitlines():
        if line and not line.startswith(b" "):
            key, _, value = line.partition(b" ")
            fields.setdefault(key, []).append(value)
    encodings = fields.get(b"encoding", [])
    if len(encodings) > 1:
        raise ValueError(f"{oid}: encoding Git duplicado")
    encoding = decode_text(encodings[0], "ascii", oid) if encodings else "utf-8"
    for key in ([b"author", b"committer"] if kind == "commit" else [b"tagger"]):
        values = fields.get(key, [])
        if len(values) != 1:
            raise ValueError(f"{oid}: campo {key.decode()} ausente ou duplicado")
        validate_identity(decode_text(values[0], "utf-8", oid), f"{oid} {key.decode()}")
    validate_message(decode_text(message, encoding, oid), oid)
    targets = fields.get(b"object", [])
    if kind == "tag" and len(targets) != 1:
        raise ValueError(f"{oid}: destino de tag ausente ou duplicado")
    return targets[0] if kind == "tag" else None


def validate_batch(objects: set[str], kind: str) -> None:
    if not objects:
        return
    output = git("cat-file", "--batch", data="\n".join(sorted(objects)).encode() + b"\n")
    offset = 0
    for expected in sorted(objects):
        end = output.index(b"\n", offset)
        oid, actual_kind, raw_size = output[offset:end].decode().split()
        if oid != expected or actual_kind != kind:
            raise ValueError(f"{expected}: objeto {kind} indisponivel")
        size = int(raw_size)
        offset = end + 1
        content = output[offset : offset + size]
        if len(content) != size or output[offset + size : offset + size + 1] != b"\n":
            raise ValueError(f"{expected}: objeto Git truncado")
        offset += size + 1
        if kind == "blob":
            validate_message(content.decode("utf-8"), f"nota {oid}")
        else:
            validate_metadata(content, kind, oid)


def validate_updates(updates: list[tuple[str, str, str]]) -> None:
    commits: set[str] = set()
    notes: set[str] = set()
    if any(set(head) != {"0"} for head, _, _ in updates):
        if git("rev-parse", "--is-shallow-repository").strip() == b"true":
            raise ValueError("historico raso: validar autoria exige historico completo")
    for head, base, ref in updates:
        if head and set(head) == {"0"}:
            continue
        head = git("rev-parse", "--verify", "--end-of-options", f"{head}^{{object}}").decode().strip()
        if base and set(base) != {"0"}:
            base = git("rev-parse", "--verify", "--end-of-options", f"{base}^{{object}}").decode().strip()
            git("cat-file", "-e", base)
        else:
            base = ""
        target = head
        kind = git("cat-file", "-t", target).decode().strip()
        while kind == "tag":
            next_target = validate_metadata(git("cat-file", "tag", target), "tag", target)
            if next_target is None:
                raise ValueError(f"{target}: destino de tag invalido")
            target = next_target.decode()
            kind = git("cat-file", "-t", target).decode().strip()
        if kind == "commit":
            args = ["rev-list", target]
            if base:
                args.extend(["--not", f"{base}^{{commit}}"])
            if ref.startswith("refs/notes/"):
                objects = git("rev-list", "--objects", "--no-object-names", *args[1:])
                entries = git("cat-file", "--batch-check=%(objectname) %(objecttype)", data=objects)
                for entry in entries.decode().splitlines():
                    oid, entry_kind = entry.split()
                    if entry_kind == "blob":
                        notes.add(oid)
                    elif entry_kind == "commit":
                        commits.add(oid)
                    elif entry_kind != "tree":
                        raise ValueError(f"{ref}: nota com objeto inesperado {entry_kind}")
            else:
                commits.update(git(*args).decode().splitlines())
        elif not ref.startswith("refs/tags/"):
            raise ValueError(f"{ref}: destino nao e commit nem tag")
    validate_batch(commits, "commit")
    validate_batch(notes, "blob")
    print(f"[autoria-git] OK: {len(commits)} commits e {len(notes)} notas validados.", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    commands.add_parser("commit-msg").add_argument("message_file", type=Path)
    commands.add_parser("pre-push")
    range_parser = commands.add_parser("range")
    range_parser.add_argument("base")
    range_parser.add_argument("head")
    args = parser.parse_args()
    try:
        if args.mode == "commit-msg":
            for field in ("GIT_AUTHOR_IDENT", "GIT_COMMITTER_IDENT"):
                validate_identity(git("var", field).decode("utf-8").strip(), field)
            encoding = git("config", "--default", "UTF-8", "--get", "i18n.commitEncoding").decode().strip()
            message = decode_text(args.message_file.read_bytes(), encoding, "mensagem do commit")
            validate_message(message, "mensagem do commit")
        elif args.mode == "range":
            validate_updates([(args.head, args.base, "HEAD")])
        else:
            updates = []
            for line in sys.stdin:
                fields = line.split()
                if len(fields) != 4:
                    raise ValueError("entrada pre-push invalida: esperados quatro campos")
                _, head, ref, base = fields
                if any(not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", oid) for oid in (head, base)):
                    raise ValueError("entrada pre-push invalida: identificador de objeto")
                updates.append((head, base, ref))
            validate_updates(updates)
    except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired) as error:
        print(f"[autoria-git][BLOQUEADO] {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from typing import Optional

import requests


def run(cmd: list[str]) -> str:
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{res.stderr}")
    return res.stdout


def get_git_diff() -> str:
    event_path = os.getenv("GITHUB_EVENT_PATH")
    event_name = os.getenv("GITHUB_EVENT_NAME", "")
    diff = ""
    try:
        if event_path and os.path.exists(event_path):
            with open(event_path, "r", encoding="utf-8") as f:
                event = json.load(f)
            if event_name == "pull_request":
                base = event.get("pull_request", {}).get("base", {}).get("sha")
                head = event.get("pull_request", {}).get("head", {}).get("sha")
                if base and head:
                    diff = run(["git", "diff", "--unified=0", "--no-color", f"{base}...{head}"])
            elif event_name == "push":
                before = event.get("before")
                after = event.get("after") or os.getenv("GITHUB_SHA")
                if before and after:
                    diff = run(["git", "diff", "--unified=0", "--no-color", f"{before}...{after}"])
    except Exception:
        pass

    if not diff:
        # Fallback: last commit diff
        try:
            diff = run(["git", "diff", "--unified=0", "--no-color", "HEAD~1...HEAD"])
        except Exception:
            diff = ""
    return diff[:200_000]  # cap to avoid excessive payloads


def build_prompt(diff: str) -> str:
    return (
        "Você é um revisor de PRs. Analise o diff abaixo e responda em Português com:\n"
        "- Principais problemas (bugs, regressões, segurança)\n"
        "- Itens de estilo/performance relevantes\n"
        "- Cobertura de testes sugerida\n"
        "- Ação recomendada (aprovar/solicitar mudanças)\n\n"
        "Use bullets concisos e cite arquivos/linhas quando possível.\n\n"
        "Diff:\n" + diff
    )


def call_anthropic(prompt: str) -> Optional[str]:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 1200,
        "messages": [{"role": "user", "content": prompt}],
    }
    r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    parts = data.get("content") or []
    if parts and isinstance(parts, list):
        return "".join(p.get("text", "") for p in parts)
    return None


def call_openai(prompt: str) -> Optional[str]:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    headers = {"authorization": f"Bearer {key}", "content-type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1200,
        "temperature": 0.2,
    }
    r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message", {}).get("content")
    return msg


def call_qwen(prompt: str) -> Optional[str]:
    key = os.getenv("DASHSCOPE_API_KEY")
    if not key:
        return None
    endpoint = os.getenv(
        "QWEN_ENDPOINT",
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
    )
    model = os.getenv("QWEN_MODEL", "qwen2.5-coder-32b-instruct")
    headers = {"authorization": f"Bearer {key}", "content-type": "application/json"}
    payload = {
        "model": model,
        "input": prompt,
        "parameters": {"result_format": "message", "max_tokens": 1200, "temperature": 0.2},
    }
    r = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    # Accept a few possible shapes
    for path in (
        ("output", "text"),
        ("output", "choices", 0, "message", "content"),
        ("choices", 0, "message", "content"),
    ):
        cur = data
        ok = True
        for k in path:
            if isinstance(k, int):
                if isinstance(cur, list) and len(cur) > k:
                    cur = cur[k]
                else:
                    ok = False
                    break
            else:
                if isinstance(cur, dict) and k in cur:
                    cur = cur[k]
                else:
                    ok = False
                    break
        if ok and isinstance(cur, str):
            return cur
    return None


def main() -> int:
    diff = get_git_diff()
    if not diff:
        print("No diff to review.")
        return 0
    prompt = build_prompt(diff)

    text = None
    # Try providers by priority unless FORCE_PROVIDER is set
    force = os.getenv("FORCE_PROVIDER", "").lower()
    providers = [
        ("anthropic", call_anthropic),
        ("openai", call_openai),
        ("qwen", call_qwen),
    ]
    if force:
        providers = [p for p in providers if p[0] == force]
    for name, fn in providers:
        try:
            text = fn(prompt)
            if text:
                print(f"[ai-review] Provider: {name}")
                break
        except Exception as e:
            print(f"[ai-review] {name} error: {e}", file=sys.stderr)
            continue

    if not text:
        text = (
            "Não foi possível contatar provedores de IA (verifique secrets).\n"
            "Segue diff resumido para revisão manual.\n\n" + diff[:8000]
        )

    os.makedirs(".github/scripts", exist_ok=True)
    out = os.path.join(".github", "scripts", "review.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from typing import Optional, List, Tuple

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


def call_openrouter(prompt: str) -> Optional[str]:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return None
    model = os.getenv("OPENROUTER_MODEL", "openrouter/auto")
    endpoint = os.getenv("OPENROUTER_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions")
    headers = {
        "authorization": f"Bearer {key}",
        "content-type": "application/json",
    }
    ref = os.getenv("OPENROUTER_REFERER")
    title = os.getenv("OPENROUTER_TITLE")
    if ref:
        headers["HTTP-Referer"] = ref
    if title:
        headers["X-Title"] = title
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1200,
        "temperature": 0.2,
    }
    r = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message", {}).get("content")
    return msg


def call_deepseek(prompt: str) -> Optional[str]:
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        return None
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-coder")
    endpoint = os.getenv("DEEPSEEK_ENDPOINT", "https://api.deepseek.com/v1/chat/completions")
    headers = {"authorization": f"Bearer {key}", "content-type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1200,
        "temperature": 0.2,
    }
    r = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message", {}).get("content")
    return msg


def call_zhipu_glm(prompt: str) -> Optional[str]:
    key = os.getenv("ZHIPU_API_KEY") or os.getenv("GLM_API_KEY")
    if not key:
        return None
    model = os.getenv("ZHIPU_MODEL", "glm-4-flash")
    endpoint = os.getenv("ZHIPU_ENDPOINT", "https://open.bigmodel.cn/api/paas/v4/chat/completions")
    headers = {"authorization": f"Bearer {key}", "content-type": "application/json"}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    r = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message", {}).get("content")
    return msg


def call_gemini(prompt: str) -> Optional[str]:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    endpoint = os.getenv(
        "GEMINI_ENDPOINT",
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    )
    url = endpoint
    if "?" in url:
        url += f"&key={key}"
    else:
        url += f"?key={key}"
    headers = {"content-type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1200}}
    r = requests.post(url, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None


def call_minimax(prompt: str) -> Optional[str]:
    key = os.getenv("MINIMAX_API_KEY")
    group = os.getenv("MINIMAX_GROUP_ID")
    if not key or not group:
        return None
    model = os.getenv("MINIMAX_MODEL", "abab6.5-chat")
    endpoint = os.getenv("MINIMAX_ENDPOINT", "https://api.minimax.chat/v1/text/chatcompletion")
    headers = {"authorization": f"Bearer {key}", "content-type": "application/json"}
    payload = {
        "model": model,
        "tokens_to_generate": 1200,
        "temperature": 0.2,
        "messages": [{"sender_type": "USER", "text": prompt}],
    }
    url = endpoint
    if "?" in url:
        url += f"&GroupId={group}"
    else:
        url += f"?GroupId={group}"
    r = requests.post(url, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    # Possible shapes: output_text, choices[0].message
    if isinstance(data, dict):
        if data.get("base_resp", {}).get("status_code") == 0:
            # new api
            texts = data.get("output", {}).get("text", [])
            if texts:
                return "\n".join(texts)
        if "choices" in data:
            ch0 = (data["choices"] or [{}])[0]
            msg = ch0.get("message", {}).get("content") or ch0.get("delta", {}).get("content")
            if msg:
                return msg
        if "output_text" in data:
            return data.get("output_text")
    return None


def call_xai_grok(prompt: str) -> Optional[str]:
    key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
    if not key:
        return None
    model = os.getenv("XAI_MODEL", "grok-2-latest")
    endpoint = os.getenv("XAI_ENDPOINT", "https://api.x.ai/v1/chat/completions")
    headers = {"authorization": f"Bearer {key}", "content-type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1200,
        "temperature": 0.2,
    }
    r = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message", {}).get("content")
    return msg


def call_kimi_moonshot(prompt: str) -> Optional[str]:
    key = os.getenv("MOONSHOT_API_KEY") or os.getenv("KIMI_API_KEY")
    if not key:
        return None
    model = os.getenv("MOONSHOT_MODEL", "moonshot-v1-8k")
    endpoint = os.getenv("MOONSHOT_ENDPOINT", "https://api.moonshot.cn/v1/chat/completions")
    headers = {"authorization": f"Bearer {key}", "content-type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1200,
        "temperature": 0.2,
    }
    r = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message", {}).get("content")
    return msg


def call_mistral(prompt: str) -> Optional[str]:
    key = os.getenv("MISTRAL_API_KEY")
    if not key:
        return None
    model = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
    endpoint = os.getenv("MISTRAL_ENDPOINT", "https://api.mistral.ai/v1/chat/completions")
    headers = {"authorization": f"Bearer {key}", "content-type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1200,
        "temperature": 0.2,
    }
    r = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message", {}).get("content")
    return msg


def main() -> int:
    diff = get_git_diff()
    if not diff:
        print("No diff to review.")
        return 0
    prompt = build_prompt(diff)

    text = None
    # Try providers by priority unless FORCE_PROVIDER is set
    force = os.getenv("FORCE_PROVIDER", "").lower()
    all_providers: List[Tuple[str, callable]] = [
        ("anthropic", call_anthropic),
        ("openai", call_openai),
        ("qwen", call_qwen),
        ("openrouter", call_openrouter),
        ("deepseek", call_deepseek),
        ("zhipu", call_zhipu_glm),
        ("gemini", call_gemini),
        ("minimax", call_minimax),
        ("xai", call_xai_grok),
        ("moonshot", call_kimi_moonshot),
        ("mistral", call_mistral),
    ]
    providers = all_providers
    if force:
        providers = [p for p in all_providers if p[0] == force]
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

AI Review – Provedores Suportados

Este repositório possui um workflow de revisão por IA para PRs que pode usar vários provedores. Basta definir os secrets/variáveis no GitHub (Settings → Secrets and variables → Actions) para habilitar o(s) provedor(es) desejado(s).

Gatilho
- Workflow: `.github/workflows/ai-review.yml`
- Dispara em pull requests não‑draft; comenta automaticamente com o review.

Ordem de tentativa (padrão)
- anthropic → openai → qwen → openrouter → deepseek → zhipu → gemini → minimax → xai → moonshot → mistral
- Para forçar um provedor específico, defina a variável `FORCE_PROVIDER` com um destes valores: `anthropic|openai|qwen|openrouter|deepseek|zhipu|gemini|minimax|xai|moonshot|mistral`.

Secrets e variáveis por provedor

Anthropic (Claude)
- Secret: `ANTHROPIC_API_KEY`
- Var opcional: `ANTHROPIC_MODEL` (ex.: `claude-3-5-sonnet-latest`)

OpenAI
- Secret: `OPENAI_API_KEY`
- Vars opcionais: `OPENAI_MODEL` (ex.: `gpt-4o-mini`)

Qwen (DashScope)
- Secret: `DASHSCOPE_API_KEY`
- Vars opcionais: `QWEN_MODEL` (ex.: `qwen2.5-coder-32b-instruct`), `QWEN_ENDPOINT`

OpenRouter
- Secret: `OPENROUTER_API_KEY`
- Vars opcionais: `OPENROUTER_MODEL` (ex.: `openrouter/auto`), `OPENROUTER_ENDPOINT`, `OPENROUTER_REFERER`, `OPENROUTER_TITLE`

DeepSeek
- Secret: `DEEPSEEK_API_KEY`
- Vars opcionais: `DEEPSEEK_MODEL` (ex.: `deepseek-coder`), `DEEPSEEK_ENDPOINT`

ZhipuAI (GLM)
- Secret: `ZHIPU_API_KEY` (ou `GLM_API_KEY`)
- Vars opcionais: `ZHIPU_MODEL` (ex.: `glm-4-flash`), `ZHIPU_ENDPOINT`

Gemini
- Secret: `GEMINI_API_KEY`
- Vars opcionais: `GEMINI_MODEL` (ex.: `gemini-1.5-flash`), `GEMINI_ENDPOINT`

Minimax
- Secrets: `MINIMAX_API_KEY`, `MINIMAX_GROUP_ID`
- Vars opcionais: `MINIMAX_MODEL` (ex.: `abab6.5-chat`), `MINIMAX_ENDPOINT`

xAI (Grok)
- Secret: `XAI_API_KEY` (ou `GROK_API_KEY`)
- Vars opcionais: `XAI_MODEL` (ex.: `grok-2-latest`), `XAI_ENDPOINT`

Moonshot (Kimi)
- Secret: `MOONSHOT_API_KEY` (ou `KIMI_API_KEY`)
- Vars opcionais: `MOONSHOT_MODEL` (ex.: `moonshot-v1-8k`), `MOONSHOT_ENDPOINT`

Mistral
- Secret: `MISTRAL_API_KEY`
- Vars opcionais: `MISTRAL_MODEL` (ex.: `mistral-large-latest`), `MISTRAL_ENDPOINT`

Dicas
- Você pode definir múltiplos secrets ao mesmo tempo; o workflow tentará na ordem listada até obter resposta.
- Para depurar, veja os logs do job “AI PR Review (optional)” no PR.
- O script do reviewer está em `.github/scripts/ai_review.py` e o prompt pode ser ajustado conforme necessidade.


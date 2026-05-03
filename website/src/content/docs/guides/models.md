---
title: Models
description: Connect any LLM provider by setting an API key and model string.
---

Cyclops Code uses [LiteLLM](https://github.com/BerriAI/litellm) to call any model. Switch providers by changing one string and setting the matching API key.

## Providers

### Anthropic

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
cyclops --model anthropic/claude-opus-4-5
cyclops --model anthropic/claude-haiku-4-5-20251001
```

### OpenAI

```bash
export OPENAI_API_KEY="sk-..."
cyclops --model gpt-4o
cyclops --model gpt-4o-mini
```

### Groq

Groq offers a generous free tier and fast inference.

```bash
export GROQ_API_KEY="gsk_..."
cyclops --model groq/llama-3.3-70b-versatile
cyclops --model groq/llama-3.1-8b-instant
```

### Google Gemini

```bash
export GEMINI_API_KEY="..."
cyclops --model gemini/gemini-2.0-flash
cyclops --model gemini/gemini-1.5-pro
```

### Ollama (local)

No API key needed. Install [Ollama](https://ollama.ai), pull a model, then run:

```bash
ollama pull qwen2.5-coder:7b
cyclops --model ollama/qwen2.5-coder:7b
```

Good models for coding tasks: `qwen2.5-coder:7b`, `qwen2.5-coder:14b`, `deepseek-coder-v2`.

### Together AI

```bash
export TOGETHERAI_API_KEY="..."
cyclops --model together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo
```

## Switching models

Pass `--model` on any invocation to override the default for that run:

```bash
cyclops --model gpt-4o "review this PR"
```

Switch mid-session with `/model` in the REPL. Type the model name or use the interactive picker with search and autocomplete.

## Setting a default

The default model is stored in `~/.cyclops/config.json`:

```json
{
  "model": "anthropic/claude-haiku-4-5-20251001"
}
```

On first launch Cyclops Code will prompt you to pick a default.

## Model strings

LiteLLM model strings follow the pattern `provider/model-name`. See the [LiteLLM provider docs](https://docs.litellm.ai/docs/providers) for the full list of supported models and their string formats.

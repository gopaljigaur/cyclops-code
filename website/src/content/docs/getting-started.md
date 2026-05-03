---
title: Getting Started
description: Install Cyclops Code and run your first task.
---

## Install

```bash
uv tool install cyclops-code
```

Python 3.10 or later is required. [uv](https://docs.astral.sh/uv/) is the recommended way to install and manage Cyclops Code.

## Set an API key

Cyclops Code uses [LiteLLM](https://github.com/BerriAI/litellm) to call any model. Set the environment variable for the provider you want to use:

```bash
# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI
export OPENAI_API_KEY="sk-..."

# Groq (fast, free tier available)
export GROQ_API_KEY="gsk_..."

# Google
export GEMINI_API_KEY="..."

# Ollama (local, no key needed)
# Install from https://ollama.ai
```

You can also add the key to your shell profile (`~/.zshrc`, `~/.bashrc`) so you do not need to export it every time.

## First run

Start the interactive REPL:

```bash
cyclops
```

Or run a one-shot task without entering the REPL:

```bash
cyclops "fix the type errors in src/auth.py"
cyclops "write tests for the payment module"
```

On first launch Cyclops Code asks you to select a default model. You can change it later with `/model` or `--model`.

## Pick a model

Pass `--model` to override the default for a single run:

```bash
cyclops --model anthropic/claude-opus-4-5 "refactor the database layer"
cyclops --model groq/llama-3.3-70b-versatile "explain this function"
cyclops --model ollama/qwen2.5-coder:7b "add docstrings"
```

See [Models](/guides/models/) for the full list of providers and model strings.

## Development install

To run from source or contribute:

```bash
git clone https://github.com/gopaljigaur/cyclops-code
cd cyclops-code
uv sync
uv run cyclops
```

To use a local build of cyclops-ai alongside cyclops-code:

```bash
uv add --editable ../cyclops
```

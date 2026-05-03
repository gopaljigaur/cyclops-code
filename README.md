<div align="center">
  <img src="./docs/assets/banner.svg" alt="cyclops code" width="900"/>

  <br/>
  <br/>

  **A coding agent for your terminal. Any model.**

  <br/>

  [Install](#install) | [Usage](#usage) | [Tools](#tools) | [MCP](#mcp) | [Config](#config)

  <br/>

  [![PyPI](https://img.shields.io/pypi/v/cyclops-code?color=58a6ff&label=PyPI)](https://pypi.org/project/cyclops-code)
  [![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://pypi.org/project/cyclops-code)
  [![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

</div>

---

cyclops code is an AI coding agent that runs in your terminal. It reads and edits files, runs shell commands, searches codebases, and fetches web content. Any model. It works with every model [LiteLLM](https://github.com/BerriAI/litellm) supports: Claude, GPT-4o, Gemini, Llama via Ollama, and 100+ more.

## Install

```bash
uv tool install cyclops-code
```

**Development (local):**

```bash
git clone https://github.com/gopaljigaur/cyclops-code
cd cyclops-code
uv sync
uv add --editable ../cyclops  # optional: use local cyclops-ai
uv run cyclops
```

## Usage

Start the interactive REPL:

```bash
cyclops
```

Run a one-shot query from the command line:

```bash
cyclops "fix the type errors in src/auth.py"
cyclops "add tests for the payment module"
cyclops --model anthropic/claude-opus-4-5 "refactor the database layer"
```

Options:

```
-m, --model TEXT       Model to use (overrides config)
--stream/--no-stream   Toggle streaming output
--cwd TEXT             Working directory (default: current dir)
```

Run shell commands directly in the REPL with `!`:

```
❯ ! git log --oneline -5
❯ ! npm test
```

## REPL

The REPL keeps conversation history across turns. The model can call tools, you can review and approve each one, and the session can be saved and resumed.

**Keyboard shortcuts**

| Key | Action |
|---|---|
| `Enter` | Submit message |
| `Alt+Enter` | Insert newline |
| `Shift+Tab` | Toggle auto / review approval mode |
| `Ctrl+O` | Expand / collapse tool output |
| `Ctrl+C` | Cancel current generation |
| `Ctrl+C` twice | Exit |
| `Ctrl+D` | Exit (on empty input) |

**Slash commands**

| Command | Description |
|---|---|
| `/help` | List all commands |
| `/clear` | Wipe history and clear screen |
| `/compact` | Summarize history via LLM to save context |
| `/model [name]` | Switch model interactively or by name |
| `/mode` | Toggle auto / review tool approval |
| `/mcp` | Manage MCP servers |
| `/save [name]` | Save session to disk |
| `/load <name>` | Load a saved session |
| `/sessions` | List saved sessions |
| `/cost` | Show token usage and estimated cost |
| `/exit` | Quit |

**Tool approval**

In `review` mode (default), each tool call shows an interactive picker before executing:

```
  ▶ Bash  rm -rf dist/

  ❯ Yes
    No
    Yes to all
```

Switch to `auto` mode with `/mode` or `Shift+Tab` to approve all tools automatically.

## Tools

| Tool | Description |
|---|---|
| `Read` | Read file contents with line numbers |
| `Write` | Create or overwrite a file |
| `Edit` | Replace exact text in a file (old string must match exactly once) |
| `Bash` | Run shell commands |
| `Glob` | Find files by glob pattern |
| `Grep` | Search file contents by regex |
| `WebFetch` | Fetch a URL as plain text |
| `Plan` | Write a step-by-step plan before starting a multi-step task |
| `PlanUpdate` | Mark a plan step as `todo`, `in_progress`, or `done` |

## MCP

Connect any MCP server as an additional tool source. Tools from connected servers appear alongside the built-in tools.

Add a server (persisted to config):

```bash
cyclops mcp add filesystem npx -- -y @modelcontextprotocol/server-filesystem .
cyclops mcp add github npx -- -y @modelcontextprotocol/server-github
cyclops mcp list
cyclops mcp remove filesystem
```

Manage servers from inside the REPL:

```
❯ /mcp list
❯ /mcp add search npx -- -y @modelcontextprotocol/server-brave-search
❯ /mcp connect search
❯ /mcp disconnect search
❯ /mcp remove search
```

## Config

Config is stored at `~/.cyclops/config.json`:

```json
{
  "model": "anthropic/claude-3-5-haiku-20241022",
  "stream": true,
  "max_iterations": 15,
  "temperature": 0.2,
  "mcp_servers": [
    {
      "name": "filesystem",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
      "env": {}
    }
  ]
}
```

Sessions are saved to `~/.cyclops/sessions/`. Command history is at `~/.cyclops/history`.

## Models

Set the API key for your provider, then pass the model string:

```bash
# Anthropic
ANTHROPIC_API_KEY=... cyclops --model anthropic/claude-opus-4-5

# OpenAI
OPENAI_API_KEY=... cyclops --model gpt-4o

# Groq (fast, free tier available)
GROQ_API_KEY=... cyclops --model groq/llama-3.3-70b-versatile

# Google
GEMINI_API_KEY=... cyclops --model gemini/gemini-2.0-flash

# Ollama (local, no key needed)
cyclops --model ollama/qwen2.5-coder:7b
```

Use `/model` in the REPL to switch interactively with autocomplete and filtering.

## License

MIT

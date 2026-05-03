---
title: The REPL
description: Interactive multi-turn coding sessions with keyboard shortcuts and slash commands.
---

Start the REPL with:

```bash
cyclops
```

The REPL keeps the full conversation history across turns. The model sees everything said earlier in the session, so you can refer back to prior context naturally.

## Keyboard shortcuts

| Key | Action |
|---|---|
| `Enter` | Submit message |
| `Alt+Enter` | Insert a newline (for multi-line messages) |
| `Shift+Tab` | Toggle between auto and review tool approval mode |
| `Ctrl+O` | Expand or collapse tool output |
| `Ctrl+C` | Cancel the current generation |
| `Ctrl+C` twice | Exit |
| `Ctrl+D` | Exit (on empty input) |

## Slash commands

| Command | Description |
|---|---|
| `/help` | List all available commands |
| `/clear` | Wipe history and clear the screen |
| `/compact` | Summarize history via the LLM to save context space |
| `/model [name]` | Switch model interactively or by name |
| `/mode` | Toggle between auto and review tool approval |
| `/mcp` | Manage MCP servers |
| `/save [name]` | Save the current session to disk |
| `/load <name>` | Load a previously saved session |
| `/sessions` | List all saved sessions |
| `/cost` | Show token usage and estimated cost for the session |
| `/exit` | Quit |

## Running shell commands

Prefix any input with `!` to run it as a shell command. The output appears inline in the REPL:

```
> ! git log --oneline -5
> ! npm test
> ! ls -la src/
```

This is useful for checking results without leaving the session.

## CLI flags

Pass these before your message for one-shot runs:

```bash
cyclops [OPTIONS] [PROMPT]

Options:
  -m, --model TEXT       Model to use (overrides config)
  --stream/--no-stream   Toggle streaming output
  --cwd TEXT             Working directory (default: current dir)
```

Example:

```bash
cyclops --model gpt-4o --no-stream "summarise this file" < notes.txt
```

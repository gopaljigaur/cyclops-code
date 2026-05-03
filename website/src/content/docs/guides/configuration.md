---
title: Configuration
description: Config file reference and all available settings.
---

Configuration is stored at `~/.cyclops/config.json`. It is created automatically on first launch.

## Full config example

```json
{
  "model": "anthropic/claude-haiku-4-5-20251001",
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

## Options

| Key | Type | Default | Description |
|---|---|---|---|
| `model` | string | set on first launch | Default model string (LiteLLM format) |
| `stream` | boolean | `true` | Stream tokens as they arrive |
| `max_iterations` | integer | `15` | Max tool call rounds per generation |
| `temperature` | float | `0.2` | Sampling temperature |
| `mcp_servers` | array | `[]` | MCP server definitions (see [MCP Servers](/guides/mcp/)) |

## CLI overrides

Any setting can be overridden per-run with a CLI flag:

```bash
cyclops --model gpt-4o --no-stream "..."
cyclops --cwd /path/to/project "..."
```

## Files

| Path | Contents |
|---|---|
| `~/.cyclops/config.json` | Settings and MCP server list |
| `~/.cyclops/sessions/` | Saved sessions |
| `~/.cyclops/history` | Command history for the REPL input |

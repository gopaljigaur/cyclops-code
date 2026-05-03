---
title: MCP Servers
description: Connect external tool sources via the Model Context Protocol.
---

Cyclops Code supports the [Model Context Protocol](https://modelcontextprotocol.io/) (MCP). Connect any MCP server and its tools become available to the agent alongside the built-in ones.

## Add a server

Use the `cyclops mcp` subcommand to add a server. The configuration is saved to `~/.cyclops/config.json` and persists across sessions.

```bash
# Filesystem access
cyclops mcp add filesystem npx -- -y @modelcontextprotocol/server-filesystem .

# GitHub integration
cyclops mcp add github npx -- -y @modelcontextprotocol/server-github

# Brave Search
cyclops mcp add search npx -- -y @modelcontextprotocol/server-brave-search
```

The format is:

```bash
cyclops mcp add <name> <command> -- [args...]
```

## List and remove servers

```bash
cyclops mcp list
cyclops mcp remove filesystem
```

## Manage from inside the REPL

You can also manage servers without leaving a session:

```
> /mcp list
> /mcp add search npx -- -y @modelcontextprotocol/server-brave-search
> /mcp connect search
> /mcp disconnect search
> /mcp remove search
```

`/mcp connect` and `/mcp disconnect` toggle a server on or off for the current session without removing it from config.

## How it works

When Cyclops Code starts, it connects to all configured MCP servers over stdio. Tools from each server appear in the agent's tool list with the server name as a prefix (e.g., `filesystem__read_file`). The agent can call them the same way as built-in tools.

## Config reference

MCP server entries in `~/.cyclops/config.json`:

```json
{
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

Use `env` to pass environment variables to the server process (e.g., API keys for search servers).

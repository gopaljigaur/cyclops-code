---
title: Built-in Tools
description: Reference for the tools available to the coding agent.
---

Cyclops Code ships with a set of tools the agent can call to read and edit files, run commands, search codebases, and fetch web content. All tools are available out of the box with no configuration.

## Tool reference

### Read

Read a file and return its contents with line numbers.

```
Read path/to/file.py
Read path/to/file.py offset=50 limit=100   # read lines 50-150
```

Useful for the agent to inspect code before editing.

### Write

Create a new file or completely overwrite an existing one.

```
Write path/to/new_file.py
```

The agent provides the full file content. Use `Edit` for targeted changes.

### Edit

Replace an exact string in a file. The old string must match exactly once in the file.

```
Edit path/to/file.py
  old_string: "return x + 1"
  new_string: "return x + 2"
```

Safer than `Write` for small changes -- only the matched section is replaced.

### Bash

Run any shell command and return its output.

```
Bash: git diff HEAD~1
Bash: npm run test -- --filter auth
Bash: python -m pytest tests/test_api.py -v
```

Commands run in the working directory Cyclops Code was started from.

### Glob

Find files matching a glob pattern.

```
Glob: src/**/*.ts
Glob: tests/test_*.py
```

Returns matching paths relative to the working directory.

### Grep

Search file contents by regular expression.

```
Grep: "def authenticate" src/
Grep: "TODO|FIXME" --include="*.py"
```

Returns matching lines with file paths and line numbers.

### WebFetch

Fetch a URL and return its content as plain text.

```
WebFetch: https://docs.example.com/api
```

Useful for looking up documentation or reading public resources.

### Plan

Write a numbered step-by-step plan before starting a complex task. The plan is stored and can be updated as steps complete.

### PlanUpdate

Mark a plan step as `todo`, `in_progress`, or `done`. Called automatically as the agent works through a plan.

## MCP tools

Tools from connected MCP servers appear alongside the built-in tools. See [MCP Servers](/guides/mcp/) for how to connect them.

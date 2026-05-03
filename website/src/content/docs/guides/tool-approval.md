---
title: Tool Approval
description: Review or auto-approve tool calls before they execute.
---

Before a tool runs, Cyclops Code shows you what it plans to do and asks for approval. This keeps you in control without interrupting the flow.

## Review mode

The default mode. Each tool call shows an interactive picker:

```
  Bash  rm -rf dist/

  > Yes
    No
    Yes to all
```

Use arrow keys to choose, then press `Enter`.

- **Yes** -- run this tool call
- **No** -- skip this tool call; the agent continues without it
- **Yes to all** -- approve all remaining tool calls in this run (switches to auto for the current generation)

## Auto mode

In auto mode every tool call is approved automatically with no prompt. Use this when you trust the task and want uninterrupted output.

Switch between modes in any of these ways:

- Press `Shift+Tab` at any time
- Type `/mode` in the REPL
- The picker's "Yes to all" option switches to auto for the current generation only

The current mode is shown in the status bar at the bottom of the REPL.

## Tip

Start in review mode to understand what the agent is doing for a new task, then switch to auto once you are confident in the direction.

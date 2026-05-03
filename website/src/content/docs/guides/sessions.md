---
title: Sessions
description: Save conversations to disk and resume them later.
---

Sessions let you pause a conversation and pick it up exactly where you left off, including the full message history and any in-progress context.

## Save a session

From inside the REPL:

```
> /save my-refactor
```

If you omit a name, a timestamp is used. Sessions are stored as JSON files in `~/.cyclops/sessions/`.

## Load a session

```
> /load my-refactor
```

The history is restored and the conversation continues from the last message.

## List saved sessions

```
> /sessions
```

Shows all saved sessions with their names and timestamps.

## From the command line

You can also load a session when starting Cyclops Code (not yet supported via a flag; use `/load` once in the REPL).

## Storage location

```
~/.cyclops/sessions/<name>.json
```

Session files are plain JSON. You can inspect or delete them manually.

## Starting fresh

To clear the current history without saving:

```
> /clear
```

This wipes the conversation and clears the screen. The model starts with no prior context.

## Compacting history

For long sessions, the full history can grow large and consume context window space. Use `/compact` to summarize the history via the LLM:

```
> /compact
```

The conversation is replaced with a single summary message. Useful before switching to a new sub-task in the same session.

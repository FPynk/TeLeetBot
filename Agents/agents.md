# AGENTS.md

## Working model for this repository

This repository contains a curated knowledge layer under `/knowledge`.
You must use it as the primary navigation layer before reading large parts of the codebase.

For every non-trivial task, follow this order:

1. Read `knowledge/system-overview.md`
2. Read the most relevant file in `knowledge/subsystems/`
3. Read the most relevant file in `knowledge/flows/`
4. Search `knowledge/repo_map.json` and `knowledge/symbol_index.json`
5. Only then open source files that appear relevant

Do not start by scanning the whole repository unless the task explicitly requires it.

## How to use the knowledge layer

Use the knowledge layer to answer:
- which subsystem owns this task
- which flow the task belongs to
- which files and symbols are most relevant
- which invariants and danger zones must be respected

Treat markdown notes as the intent layer and JSON files as the structure layer.

## Editing behaviour

Before making code changes:
- identify the likely subsystem
- identify the likely flow
- list the smallest set of files needed for the task

After making code changes:
- check whether `/knowledge` is now stale
- update only the relevant knowledge files
- do not rewrite the entire knowledge layer

## When to update `/knowledge`

Update `/knowledge` if you changed any of the following:
- subsystem boundaries or responsibilities
- important execution flows
- major entry points
- high-value symbols in `repo_map.json` or `symbol_index.json`
- important invariants, gotchas, or danger zones

Do not update `/knowledge` for trivial formatting-only or local refactors unless paths, symbols, or behaviour materially changed.

## Output expectations

For implementation tasks, always report:
- subsystem selected
- flow selected
- files read
- whether `/knowledge` was updated
- if not updated, why no update was necessary

## Constraints

- Be concise
- Prefer the smallest correct change
- Do not invent architecture not supported by the code
- If the knowledge layer appears stale or incomplete, say so explicitly
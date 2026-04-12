# Knowledge Layer

## What This Is For
- A lightweight, manually curated map of the highest-leverage parts of the repo.
- It is meant to help a future agent find the right files, symbols, flows, and constraints before reading large parts of `src/`.
- It is intentionally incomplete. The goal is faster navigation, not full documentation coverage.

## What Is Included
- `system-overview.md`: short orientation for architecture, storage, jobs, and danger zones
- `subsystems/`: one note per important subsystem only
- `flows/`: one note per important execution flow only
- `repo_map.json`: compact machine-readable map of important files and symbols
- `symbol_index.json`: flatter retrieval-oriented index of important symbols

## What Is Not Included
- Trivial helpers, generic formatting code, most debug-only paths, or every small DB accessor
- Tests, generated files, lockfiles, vendor-style content, and one-off notes
- Full call graphs or exhaustive function inventories

## Maintenance Rules
- Keep it small. If a file or symbol is not useful for common agent tasks, leave it out.
- Prefer stable orchestration code, persistence code, handlers, clients, and jobs over leaf helpers.
- When architecture changes, update the subsystem note, the relevant flow note, and then the JSON indices together.
- If behavior is unclear from code, say so explicitly instead of inferring.

## Manual Vs Auto-Generated
- Everything in this directory is currently manually curated.
- The JSON files are machine-readable, but they are not generated from an AST or CI job.
- If a future automation step is added, document that here and keep hand-written notes focused on judgment and invariants.

## How Future Agents Should Use This
1. Read `system-overview.md`.
2. Read the one subsystem note that matches the task.
3. Read the matching flow note if the task changes runtime behavior.
4. Use `repo_map.json` or `symbol_index.json` to jump straight to the most relevant files and symbols.
5. Only then expand into the source files that sit on the critical path for the task.

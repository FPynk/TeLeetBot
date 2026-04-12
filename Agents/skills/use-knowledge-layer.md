---
name: use-knowledge-layer
description: Use this when starting any non-trivial task in this repository to navigate via /knowledge before reading many source files.
---

# Purpose

Use the repository knowledge layer to narrow the search space before opening source files.

# When to use

Use this skill when:
- the task touches multiple files
- the task is in an unfamiliar area
- the task involves debugging, feature work, refactoring, or architecture questions
- the repo is large enough that reading everything would be wasteful

Do not use this skill for:
- tiny single-file edits with obvious scope
- pure formatting tasks
- tasks already scoped to one exact file and symbol

# Workflow

1. Read `knowledge/system-overview.md`
2. Identify the most likely subsystem
3. Read the matching file in `knowledge/subsystems/`
4. Identify the most likely flow
5. Read the matching file in `knowledge/flows/`
6. Search `knowledge/repo_map.json` and `knowledge/symbol_index.json`
7. Produce a short working set:
   - subsystem
   - flow
   - key symbols
   - likely files
8. Only then open source files

# Required output before coding

Before making edits, report:

- **Subsystem**
- **Flow**
- **Key symbols**
- **Files to inspect first**
- **Known invariants / danger zones**

# Search discipline

Prefer reading:
- entry points
- orchestration code
- DB-touching code
- API handlers
- background jobs
- external API clients

Avoid reading:
- test files unless debugging tests
- generated files
- build artefacts
- trivial helpers unless many important paths depend on them

# If the knowledge layer is incomplete

If `/knowledge` is missing a relevant subsystem, flow, or symbol:
- continue with best-effort source inspection
- explicitly note the missing knowledge
- propose a minimal update to `/knowledge` after the code task
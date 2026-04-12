---
name: refresh-knowledge-layer
description: Use this after code changes to check whether /knowledge is stale and update only the relevant knowledge files.
---

# Purpose

Keep `/knowledge` accurate after meaningful code changes.

# When to use

Use this skill after:
- adding or removing important entry points
- changing subsystem responsibilities
- changing important execution flows
- renaming or moving important files or symbols
- changing critical invariants or danger zones
- adding important DB access, external API integrations, jobs, schedulers, or handlers

Do not use this skill after:
- trivial formatting changes
- comments-only edits
- local refactors that do not change behaviour, paths, ownership, or major symbols

# Workflow

1. Review the code changes
2. Decide whether `/knowledge` is affected
3. Update only the relevant files:
   - `knowledge/system-overview.md`
   - one or more subsystem notes
   - one or more flow notes
   - `knowledge/repo_map.json`
   - `knowledge/symbol_index.json`
4. Keep edits minimal and evidence-based
5. Do not rewrite unrelated sections

# Update rules

## Update `system-overview.md` only if:
- main subsystems changed
- major high-level flows changed
- storage systems changed
- external dependency patterns changed
- danger zones changed materially

## Update subsystem notes if:
- a subsystem's purpose or boundary changed
- its entry points changed
- important dependencies changed
- invariants changed
- common agent starting points changed

## Update flow notes if:
- trigger/entry point changed
- step order changed
- key files or symbols changed
- side effects changed
- failure points or gotchas changed

## Update `repo_map.json` and `symbol_index.json` if:
- important symbols were added, removed, renamed, or moved
- important file paths changed
- related-symbol relationships changed materially

# Required final report

Report:

- **Was `/knowledge` updated?**
- **Which files changed?**
- **Why each file changed**
- **What did not need updating**
- **Any remaining stale or uncertain areas**
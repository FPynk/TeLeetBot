# LeetCode Ingestion And Scoring

## Purpose
- Poll LeetCode for recent accepted submissions, cache problem metadata, deduplicate solves, and compute score and week-window logic.

## Main Files And Directories
- `src/poller.py`
- `src/leetcode.py`
- `src/leaderboard.py`
- `src/scoring.py`
- `src/timeutil.py`

## Entry Points
- `LCClient.recent_ac()`
- `LCClient.problem_meta()`
- `poll_loop()`
- `rank_rows()`
- `parse_weights()`
- `week_window_cst()`

## Key Symbols
- `LCClient`
- `LCClient.recent_ac`
- `LCClient.problem_meta`
- `poll_loop`
- `rank_rows`
- `parse_weights`
- `week_window_cst`

## Dependencies
- `httpx` calls to LeetCode GraphQL
- `src/db.py` for user cursors, problem cache, completions, memberships, and counts
- `src/bot.py` and `src/discord_bot.py` for outbound announcements

## Invariants
- The poller only checks users returned by `db.get_tracked_users()`.
- `recent_ac()` normalizes LeetCode timestamps to integers.
- The poller asks for only the latest 12 accepted submissions per user.
- New problem metadata is fetched lazily when a completion references an unknown slug.
- Weekly score totals depend on `week_window_cst()` and per-chat or per-channel scoring strings.
- `rank_rows()` tie-breaks by total score, then hard count, then medium count.

## Common Tasks
- Change the LeetCode GraphQL queries
- Adjust poll frequency or solve-ingestion behavior
- Change score weights or tie-break rules
- Change week boundaries or timezone handling
- Diagnose missed solves, duplicate solves, or stale problem metadata

## Related Flows
- [solve-ingestion-and-announcements](../flows/solve-ingestion-and-announcements.md)
- [membership-and-leaderboards](../flows/membership-and-leaderboards.md)
- [scheduled-summaries](../flows/scheduled-summaries.md)

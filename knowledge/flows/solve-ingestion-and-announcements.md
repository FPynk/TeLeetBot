# Solve Ingestion And Announcements

## Trigger And Entry Point
- Background trigger: `src/poller.py::poll_loop()`
- First run starts a few seconds after process boot

## Step-By-Step Path
1. `poll_loop()` gets active shared users from `db.get_tracked_users()`.
2. For each user, it loads the LeetCode cursor with `get_or_set_last_seen(lc_username)`.
3. `LCClient.recent_ac(lc_username, limit=12)` fetches recent accepted submissions from LeetCode GraphQL.
4. The poller filters submissions whose `timestamp` is newer than `last_seen` and sorts them oldest to newest.
5. For each new submission, the poller processes the solve in timestamp order.
6. If the problem slug is not in `problems`, `LCClient.problem_meta()` fetches title and difficulty and `upsert_problem()` caches it.
7. `insert_completion(user_id, slug, ts)` decides whether this solve is new enough to count.
8. If a completion was inserted, the poller reads current-week counts with `get_user_counts(user_id, start, end)`.
9. For each Telegram chat in `get_user_chats(user_id)` with `post_on_solve=1`, it computes the weighted score and sends a solve announcement.
10. For each Discord channel in `get_user_discord_channels(user_id)` with `post_on_solve=1`, it does the same.
11. After each processed submission, `get_or_set_last_seen(lc_username, ts)` advances the cursor.
12. The loop sleeps briefly between users, then waits `POLL_SEC` seconds before the next full scan.

## Key Files And Symbols
- `src/poller.py::poll_loop`
- `src/leetcode.py::LCClient.recent_ac`
- `src/leetcode.py::LCClient.problem_meta`
- `src/db.py::get_tracked_users`
- `src/db.py::get_or_set_last_seen`
- `src/db.py::insert_completion`
- `src/db.py::get_user_chats`
- `src/db.py::get_user_discord_channels`
- `src/bot.py::send_telegram_solve_announcement`
- `src/discord_bot.py::send_discord_solve_announcement`

## Side Effects
- External HTTP calls to LeetCode
- Inserts into `problems` and `completions`
- Updates `last_seen`
- Sends Telegram and Discord messages

## Failure Points And Gotchas
- The poller only fetches 12 recent ACs per user. If a user solves more than 12 problems between polls, older solves can be skipped.
- `last_seen` is stored per `lc_username`, so username switches must update that cursor correctly.
- `insert_completion()` suppresses repeat solves unless the prior solve is at least 30 days old.
- Per-user failures are logged and skipped; the outer loop keeps running.
- Discord send failures can happen because `_resolve_channel()` could not fetch the channel or because send itself failed.

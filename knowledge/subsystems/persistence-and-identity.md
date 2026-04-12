# Persistence And Identity

## Purpose
- Own the SQLite schema, cross-platform user identity model, membership state, solve history, and leaderboard queries.

## Main Files And Directories
- `src/db.py`

## Entry Points
- `init`
- `link_telegram_account`, `relink_telegram_account`, `unlink_telegram_account`
- `link_discord_account`, `relink_discord_account`, `unlink_discord_account`
- `set_chat`, `set_discord_channel`, `join_chat`, `leave_chat`, `join_discord_channel`, `leave_discord_channel`
- `get_tracked_users`, `get_or_set_last_seen`, `insert_completion`
- `get_user_counts`, `weekly_counts`, `weekly_counts_discord`

## Key Symbols
- `init`
- `link_telegram_account`
- `relink_telegram_account`
- `unlink_telegram_account`
- `link_discord_account`
- `relink_discord_account`
- `unlink_discord_account`
- `get_or_set_last_seen`
- `insert_completion`
- `weekly_counts`
- `weekly_counts_discord`

## Dependencies
- Used by every command surface and every background job
- Stores data in `bot.db` via `sqlite3`
- Depends on `problems` rows being populated before solve counts can be grouped by difficulty

## Invariants
- `users.id` is the shared internal identity across Telegram and Discord.
- `users.lc_username` is unique.
- Each Telegram account and each Discord account can point at only one shared user row.
- `last_seen` is keyed by `lc_username`, not by platform account or shared `user_id`.
- Active completions are unique by `(user_id, slug)` through the partial unique index on `is_deleted=0`.
- `insert_completion()` only counts a repeat solve if the prior active solve is at least 30 days old.
- `unlink_*()` removes platform-specific memberships first, then deletes the shared user only if no platform links remain.
- Legacy migration logic only covers the older Telegram-primary schema detected by a `telegram_user_id` column on `users`.

## Common Tasks
- Change schema or migration behavior
- Fix account linking or relinking bugs
- Change what unlinking cleans up
- Adjust leaderboard aggregation queries
- Investigate duplicate or missing completion rows

## Related Flows
- [account-linking](../flows/account-linking.md)
- [membership-and-leaderboards](../flows/membership-and-leaderboards.md)
- [solve-ingestion-and-announcements](../flows/solve-ingestion-and-announcements.md)
- [scheduled-summaries](../flows/scheduled-summaries.md)

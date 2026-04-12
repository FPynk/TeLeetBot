# Membership And Leaderboards

## Trigger And Entry Point
- Membership toggles:
  - Telegram: `/join`, `/leave`, `/postonsolve`
  - Discord: `/join`, `/leave`, `/toggle_announcements`
- Read paths:
  - Telegram: `/leaderboard`, `/stats`
  - Discord: `/leaderboard`, `/stats`

## Step-By-Step Path
1. A command handler resolves the current chat or Discord guild/channel context.
2. `set_chat()` or `set_discord_channel()` upserts the container object and optionally updates announcement or scoring settings.
3. `join_chat()` or `join_discord_channel()` inserts the membership row for the shared `user_id` behind the current platform account.
4. `leave_chat()` or `leave_discord_channel()` removes the membership row.
5. For `/leaderboard`, the handler computes the current week window with `week_window_cst()`.
6. The handler reads aggregated counts with `weekly_counts()` or `weekly_counts_discord()`.
7. `rank_rows()` applies the scoring tuple and tie-break rules.
8. Platform-specific helpers format and send the result.
9. For `/stats`, the handler uses `get_user_counts()` for lifetime totals and current-week totals.

## Key Files And Symbols
- `src/commands.py`
- `src/bot.py::leaderboard`
- `src/bot.py::stats`
- `src/discord_commands.py::register_discord_commands`
- `src/db.py::set_chat`
- `src/db.py::set_discord_channel`
- `src/db.py::join_chat`
- `src/db.py::join_discord_channel`
- `src/db.py::weekly_counts`
- `src/db.py::weekly_counts_discord`
- `src/leaderboard.py::rank_rows`
- `src/timeutil.py::week_window_cst`

## Side Effects
- Writes chat or channel rows on first use
- Writes or deletes membership rows
- Reads solve history and computes current standings

## Failure Points And Gotchas
- Telegram membership commands are private-chat guarded; Discord commands are guild-only.
- Telegram `/leaderboard` calls `set_chat()` on read, so simply viewing a board refreshes chat metadata.
- Default scoring is `"1,2,5"` unless a chat or channel row overrides it.
- Weekly windows are Monday 00:00 to next Monday 00:00 in `America/Chicago`.
- `/stats` only reports the caller's shared user; there is no general target-user lookup path.

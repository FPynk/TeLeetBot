# Telegram Interface

## Purpose
- Expose Telegram commands, resolve Telegram display names, and send leaderboard or solve-announcement messages.

## Main Files And Directories
- `src/bot.py`
- `src/commands.py`

## Entry Points
- `start_telegram()`
- Telegram handlers in `src/commands.py`: `/start`, `/help`, `/uptime`, `/link`, `/unlink`, `/relink`, `/join`, `/leave`, `/postonsolve`
- Telegram handlers in `src/bot.py`: `/leaderboard`, `/stats`, plus debug-only handlers

## Key Symbols
- `start_telegram`
- `send_telegram_solve_announcement`
- `post_telegram_leaderboard`
- `post_telegram_champion`
- `leaderboard`
- `stats`
- `link`
- `relink`
- `unlink`
- `join`
- `leave`
- `postflag`

## Dependencies
- `aiogram` `Bot`, `Dispatcher`, `Router`, and command filters
- `src/db.py` for all state reads and writes
- `src/leaderboard.py`, `src/scoring.py`, and `src/timeutil.py` for leaderboard reads
- `src/leetcode.py` only for Telegram debug handlers

## Invariants
- `BOT_TOKEN` must exist before this module can be imported successfully.
- Telegram command handling is split across two files: `src/commands.py` owns most account and membership commands, while `src/bot.py` owns leaderboard, stats, and outbound Telegram messaging helpers.
- `/join` and `/leave` are group-only behaviors.
- Name rendering prefers live `get_chat_member()` lookup, then falls back to cached username, then LeetCode username.
- Outbound leaderboard and solve messages use HTML parse mode.

## Common Tasks
- Add a Telegram command
- Change Telegram wording or formatting for live announcements
- Adjust how names are resolved in groups
- Diagnose Telegram-only link or membership issues

## Related Flows
- [startup-and-runtime](../flows/startup-and-runtime.md)
- [account-linking](../flows/account-linking.md)
- [membership-and-leaderboards](../flows/membership-and-leaderboards.md)
- [solve-ingestion-and-announcements](../flows/solve-ingestion-and-announcements.md)

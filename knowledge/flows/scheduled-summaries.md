# Scheduled Summaries

## Trigger And Entry Point
- Registered in `src/scheduler.py::start_schedulers()`
- Jobs executed by APScheduler inside the bot process

## Step-By-Step Path
1. `start_schedulers()` creates a process-level `AsyncIOScheduler` if one does not already exist.
2. It registers `weekly_leaderboards()` using a cron trigger with `hour=20` and `timezone="America/Chicago"`.
3. It registers `weekly_champion()` using a `CronTrigger` for Sunday 23:59 Chicago time.
4. `weekly_leaderboards()` computes the current week window, iterates all Telegram chats, reads `weekly_counts()`, ranks rows, and posts leaderboard snapshots.
5. The same function then iterates all Discord channels, reads `weekly_counts_discord()`, ranks rows, and posts Discord leaderboard snapshots.
6. `weekly_champion()` repeats the same read path, then posts champion messages instead of snapshot leaderboards.

## Key Files And Symbols
- `src/scheduler.py::start_schedulers`
- `src/scheduler.py::weekly_leaderboards`
- `src/scheduler.py::weekly_champion`
- `src/db.py::get_all_telegram_chats`
- `src/db.py::get_all_discord_channels`
- `src/db.py::weekly_counts`
- `src/db.py::weekly_counts_discord`
- `src/leaderboard.py::rank_rows`
- `src/bot.py::post_telegram_leaderboard`
- `src/bot.py::post_telegram_champion`
- `src/discord_bot.py::post_discord_leaderboard`
- `src/discord_bot.py::post_discord_champion`

## Side Effects
- Sends scheduled summary messages to every configured Telegram chat and Discord channel that has non-empty weekly counts
- Reads large portions of the completion history for the current week window

## Failure Points And Gotchas
- The leaderboard snapshot job is daily at 20:00 Chicago time, not weekly.
- Empty chats and channels are skipped silently.
- Scheduler setup is idempotent only because jobs use stable ids and `replace_existing=True`.
- Both jobs use the same `week_window_cst()` logic as ad hoc `/leaderboard` requests, so any timezone or scoring bug will affect both read paths.

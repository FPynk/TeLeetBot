# Runtime Orchestration

## Purpose
- Boot the process, initialize storage, start transport clients, and register long-running in-process jobs.

## Main Files And Directories
- `src/main.py`
- `src/config.py`
- `src/scheduler.py`

## Entry Points
- `src/main.py::main()`
- `src/scheduler.py::start_schedulers()`
- `src/scheduler.py::start_poller()`
- `src/config.py::discord_enabled()`

## Key Symbols
- `main`
- `discord_enabled`
- `start_schedulers`
- `start_poller`
- `weekly_leaderboards`
- `weekly_champion`

## Dependencies
- Calls into `src/db.py` before any bot runtime starts
- Starts Telegram via `src/bot.py::start_telegram()`
- Optionally starts Discord via `src/discord_bot.py::start_discord()`
- Launches the shared LeetCode poller in `src/poller.py`
- Uses APScheduler and `zoneinfo` for recurring jobs

## Invariants
- `db.init()` runs before any polling or command handling.
- If Discord is enabled, the shared poller does not start until `wait_for_discord_ready()` completes.
- `_SCHEDULER` and `_POLL_TASK` are treated as process-level singletons.
- Scheduler time is hard-coded to `America/Chicago`.
- `weekly_leaderboards()` is scheduled daily at 20:00 Chicago time despite its name.

## Common Tasks
- Add or remove a startup step
- Change env gating or startup fallback behavior
- Adjust poll cadence or scheduled summary times
- Diagnose why Discord startup can disable only Discord while Telegram keeps running

## Related Flows
- [startup-and-runtime](../flows/startup-and-runtime.md)
- [scheduled-summaries](../flows/scheduled-summaries.md)
- [solve-ingestion-and-announcements](../flows/solve-ingestion-and-announcements.md)

# Startup And Runtime

## Trigger And Entry Point
- Process start via `python -m src.main`
- Main entry: `src/main.py::main()`

## Step-By-Step Path
1. `main()` calls `db.init()` to migrate legacy schema if needed, create current tables, and ensure indexes.
2. Telegram polling is started with `asyncio.create_task(start_telegram(), name="telegram-client")`.
3. If `discord_enabled()` is true, `start_discord()` is started as another task.
4. `wait_for_discord_ready()` waits until the Discord client is ready. If Discord startup fails, the exception is logged, the Discord task is cancelled or consumed, and runtime continues without Discord.
5. `start_schedulers()` registers APScheduler jobs.
6. `start_poller()` creates the shared `poll_loop()` task.
7. `asyncio.gather(*tasks)` keeps transport tasks alive.

## Key Files And Symbols
- `src/main.py::main`
- `src/db.py::init`
- `src/bot.py::start_telegram`
- `src/discord_bot.py::start_discord`
- `src/discord_bot.py::wait_for_discord_ready`
- `src/scheduler.py::start_schedulers`
- `src/scheduler.py::start_poller`

## Side Effects
- Creates or migrates the SQLite schema
- Starts long-polling and websocket clients
- Syncs Discord slash commands during `setup_hook()`
- Schedules recurring jobs and starts the LeetCode polling loop

## Failure Points And Gotchas
- Importing `src/config.py` fails fast if `BOT_TOKEN` is unset.
- Discord is optional only when both Discord env vars are unset; partial config raises an assertion.
- The shared poller intentionally waits for Discord readiness when Discord is enabled.
- `LCClient` instances in runtime modules are long-lived; there is no explicit shutdown path that closes the underlying `httpx.AsyncClient`.

# System Overview

## What It Does
- Runs a Telegram bot and an optional Discord bot that track first-time accepted LeetCode solves for linked users.
- Persists solves and memberships in SQLite, computes weekly scores, posts live solve announcements, and sends scheduled summary messages.

## Main Subsystems
- Runtime orchestration: `src/main.py`, `src/config.py`, `src/scheduler.py`
- Persistence and shared identity: `src/db.py`
- Telegram interface: `src/bot.py`, `src/commands.py`
- Discord interface: `src/discord_bot.py`, `src/discord_commands.py`
- LeetCode ingestion and scoring: `src/poller.py`, `src/leetcode.py`, `src/leaderboard.py`, `src/scoring.py`, `src/timeutil.py`
- Deployment and ops: `Dockerfile`, `docker-compose.yml`, `.github/workflows/deploy.yaml`

## High-Level Request And Data Flow
- `src/main.py::main()` initializes the database schema and indexes with `db.init()`.
- Telegram polling starts immediately. Discord starts only when both `DISCORD_BOT_TOKEN` and `DISCORD_APP_ID` are set.
- If Discord is enabled, `wait_for_discord_ready()` blocks shared poller startup until Discord can actually send messages.
- Telegram and Discord commands mostly delegate state changes and reads to `src/db.py`.
- `src/poller.py::poll_loop()` polls LeetCode, inserts new solves, and fans out optional solve announcements to joined chats and channels.
- APScheduler jobs in `src/scheduler.py` read weekly counts from SQLite and post periodic leaderboard or champion messages.

## Storage Systems
- SQLite `bot.db`
- Core tables: `users`, `telegram_links`, `discord_links`, `chats`, `memberships`, `discord_channels`, `discord_channel_memberships`, `problems`, `completions`, `last_seen`
- Local dev uses repo-root `bot.db`; Docker Compose mounts `./data/bot.db` to `/app/bot.db`

## Background Job Systems
- In-process poller: `src/poller.py::poll_loop()` every `POLL_SEC` seconds after a short startup delay
- In-process scheduler: APScheduler in `src/scheduler.py`
- No external queue, worker pool, or separate scheduler process

## External Dependencies
- Telegram Bot API via `aiogram`
- Discord gateway and slash commands via `discord.py`
- LeetCode GraphQL via `httpx` and `https://leetcode.com/graphql`
- SQLite via `sqlite3`
- Deployment path uses Docker, GHCR, and Tailscale SSH

## Danger Zones
- `BOT_TOKEN` is required on import, so Discord-only runtime is not supported by the current config layer.
- Shared identity is cross-platform. `users.id` is the durable internal user; Telegram and Discord rows link to it.
- `last_seen` is keyed by `lc_username`, not `user_id`. Link-switch behavior depends on updating that cursor correctly.
- `completions` enforces one active `(user_id, slug)` row. A re-solve only counts again after 30 days; the older row is soft-deleted.
- Weekly windows are anchored to `America/Chicago` in both ad hoc leaderboards and scheduled jobs.
- `weekly_leaderboards()` is named "weekly" but is scheduled daily at 20:00 Chicago time.
- The poller only asks LeetCode for the most recent 12 ACs per user. Large bursts between polls can be missed.

## Where An Agent Should Start
- New Telegram command: `src/commands.py`, then `src/bot.py` if it needs leaderboard or announcement helpers
- New Discord slash command: `src/discord_commands.py`, `src/discord_bot.py`
- Linking, relinking, unlinking, or membership bugs: `src/db.py`
- Missing or duplicate solve ingestion: `src/poller.py`, `src/leetcode.py`, `src/db.py::insert_completion()`
- Scoring or week-boundary change: `src/scoring.py`, `src/timeutil.py`, `src/leaderboard.py`, then callers in `src/bot.py`, `src/discord_commands.py`, `src/scheduler.py`
- Deploy or container issue: `Dockerfile`, `docker-compose.yml`, `.github/workflows/deploy.yaml`

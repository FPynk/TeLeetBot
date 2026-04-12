# Discord Interface

## Purpose
- Run the Discord client, sync slash commands, resolve mentions, and send leaderboard or solve-announcement messages.

## Main Files And Directories
- `src/discord_bot.py`
- `src/discord_commands.py`

## Entry Points
- `TeLeetDiscordClient.setup_hook()`
- `start_discord()`
- `wait_for_discord_ready()`
- `register_discord_commands()`

## Key Symbols
- `TeLeetDiscordClient`
- `TeLeetDiscordClient.setup_hook`
- `start_discord`
- `wait_for_discord_ready`
- `register_discord_commands`
- `send_discord_solve_announcement`
- `post_discord_leaderboard`
- `post_discord_champion`

## Dependencies
- `discord.py` client, app command tree, and permission helpers
- `src/db.py` for links, memberships, and leaderboard queries
- `src/leaderboard.py` and `src/timeutil.py` for leaderboard reads
- `src/discord_render.py` for message formatting

## Invariants
- Discord support is enabled only when both `DISCORD_BOT_TOKEN` and `DISCORD_APP_ID` are set.
- Slash commands are registered inside `register_discord_commands()` during `setup_hook()`.
- If `DISCORD_DEV_GUILD_ID` is set, commands are copied and synced to that guild instead of relying on global sync only.
- `wait_for_discord_ready()` exists to keep the shared poller from sending Discord messages before the client is ready.
- Command handlers are guild-only.
- `/toggle_announcements` additionally requires `Manage Channels` or `Administrator`.

## Common Tasks
- Add or modify a slash command
- Change command sync behavior for dev or production guilds
- Adjust mention rendering or channel resolution
- Diagnose startup races or missing Discord announcements

## Related Flows
- [startup-and-runtime](../flows/startup-and-runtime.md)
- [account-linking](../flows/account-linking.md)
- [membership-and-leaderboards](../flows/membership-and-leaderboards.md)
- [solve-ingestion-and-announcements](../flows/solve-ingestion-and-announcements.md)

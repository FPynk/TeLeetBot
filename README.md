# TeLeetBot
Telegram and Discord bots to track LeetCode progress for groups of people

# Bot Commands
## Telegram
### Core
`/start`
- Where: DM
- Who: Anyone
- What: Intro + basic instructions.

`/help`
- Where: DM or Group
- Who: Anyone
- What: Basic instructions to run.

`/help -c`
- Where: DM or Group
- Who: Anyone
- What: Command overview for common flows like linking, joining, leaderboard usage, stats, and announcement toggles.

`/uptime`
- Where: DM or Group
- Who: Anyone
- What: Shows how long the bot process has been running.

`/link <leetcode_username>`
- Where: DM or Group
- Who: Anyone
- What: Links your Telegram account to your LeetCode handle and starts tracking from now (requires public LC profile).
- Usage: /link FluorescentPink

`/unlink`
- Where: DM
- Who: Anyone
- What: Unlinks your Telegram account and removes your Telegram group memberships. If this was your last linked platform, the shared user and tracked data are deleted.

`/relink <leetcode_username>`
- Where: DM or Group
- Who: Anyone
- What: Reassigns an existing LeetCode link to your current Telegram account. Use if your Telegram account changed and the bot can’t resolve you.
- Usage: /relink FluorescentPink

`/join`
- Where: Group
- Who: Anyone
- What: Opts you into this chat’s leaderboard.

`/leave`
- Where: Group
- Who: Anyone
- What: Removes you from this chat’s leaderboard.

`/leaderboard`
- Where: Group
- Who: Anyone
- What: Shows this week’s leaderboard (Mon 00:00 to next Mon 00:00, America/Chicago) using the configured weights.

`/stats`
- Where: DM or Group
- Who: Anyone
- What: Shows your lifetime totals and current-week breakdown (E/M/H).

### Admin (group)
`/postonsolve on|off`
- Where: Group
- Who: Group admin
- What: Toggles instant solve announcements for this chat (leaderboard still works when off).
- Usage: /postonsolve off

## Discord
### Core
`/help`
- Where: Server channel
- Who: Anyone
- What: Command overview for common flows like linking, joining, leaderboard usage, stats, and announcement toggles.

`/uptime`
- Where: Server channel
- Who: Anyone
- What: Shows how long the bot process has been running.

`/link <leetcode_username>`
- Where: Server channel
- Who: Anyone
- What: Links your Discord account to your LeetCode handle and starts tracking from now (requires public LC profile).

`/unlink`
- Where: Server channel
- Who: Anyone
- What: Unlinks your Discord account and removes your Discord channel memberships. If this was your last linked platform, the shared user and tracked data are deleted.

`/relink <leetcode_username>`
- Where: Server channel
- Who: Anyone
- What: Reassigns an existing LeetCode link to your current Discord account. Use if your Discord account changed.

`/join`
- Where: Server channel
- Who: Anyone
- What: Opts you into this channel’s leaderboard.

`/leave`
- Where: Server channel
- Who: Anyone
- What: Removes you from this channel’s leaderboard.

`/leaderboard`
- Where: Server channel
- Who: Anyone
- What: Shows this week’s leaderboard (Mon 00:00 to next Mon 00:00, America/Chicago) using the configured weights.

`/stats`
- Where: Server channel
- Who: Anyone
- What: Shows your lifetime totals and current-week breakdown (E/M/H).

### Admin (server channel)
`/toggle_announcements on|off`
- Where: Server channel
- Who: Manage Channels or Administrator
- What: Toggles instant solve announcements for this channel (leaderboard still works when off).

```
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
touch .env
echo 'BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN' > .env
# Optional Discord support
echo 'DISCORD_BOT_TOKEN=YOUR_DISCORD_BOT_TOKEN' >> .env
echo 'DISCORD_APP_ID=YOUR_DISCORD_APP_ID' >> .env
# Optional: faster dev command sync to one Discord server
echo 'DISCORD_DEV_GUILD_ID=YOUR_DISCORD_SERVER_ID' >> .env
python -m src.main   # quick smoke test; Ctrl+C to stop
```

For powershell
`.\.venv\Scripts\Activate.ps1`

Discord setup notes:
- Invite the Discord bot with the `bot` and `applications.commands` scopes
- Grant it `View Channels` and `Send Messages`
- `DISCORD_DEV_GUILD_ID` is optional; when set, slash commands sync to that guild instead of waiting on global sync only

Runtime notes:
- Discord support is optional and only starts when both `DISCORD_BOT_TOKEN` and `DISCORD_APP_ID` are set
- Telegram and Discord can point at the same shared LeetCode user
- `/join` and `/leave` are chat or channel scoped; linking alone does not put you on a leaderboard

Todo:
- Improve functionality

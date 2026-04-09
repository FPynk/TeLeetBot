# TeLeetBot
Telegram and Discord bots to track LeetCode progress for groups of people

# Bot Commands
## Core
`/start`
- Where: DM
- Who: Anyone
- What: Intro + basic instructions.

`/help`
- Where: DM or Group
- Who: Anyone
- What: Basic instructions to run

`/link <leetcode_username>`
- Where: DM or Group
- Who: Anyone
- What: Links your Telegram account to your LeetCode handle and starts tracking from now (requires public LC profile).
- Usage: /link FluorescentPink

`/unlink`
- Where: DM
- Who: Anyone
- What: Unlinks your account and deletes your data (memberships, completions, last_seen). You can /link again later.

`/relink <leetcode_username>`
- Where: DM or Group
- Who: Anyone
- What: Reassigns an existing LeetCode link to your current Telegram account (migrates memberships/completions). Use if your Telegram account changed and the bot can’t resolve you.
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
- What: Shows this week’s leaderboard (Mon–Sun, CST) using weights E=1, M=2, H=5.

`/stats`
- Where: DM or Group
- Who: Anyone
- What: Shows your lifetime totals and current-week breakdown (E/M/H).
- Note: Targeting another user by mention is planned; current MVP shows the caller’s stats.

## Admin (group)
`/postonsolve on|off`
- Where: Group
- Who: Group admin
- What: Toggles instant “🎉 solved …” announcements for this chat (leaderboard still works when off).
- Usage: /postonsolve off

```
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
touch .env
echo 'BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN' > .env
python -m src.main   # quick smoke test; Ctrl+C to stop
```

For powershell
`.\.venv\Scripts\Activate.ps1`

Discord setup notes:

- Add `DISCORD_BOT_TOKEN` and `DISCORD_APP_ID` to `.env`
- Optional: add `DISCORD_DEV_GUILD_ID` for faster guild-scoped slash command sync during development
- Invite the Discord bot with the `bot` and `applications.commands` scopes
- Grant it `View Channels` and `Send Messages`

Todo:
- Improve functionality

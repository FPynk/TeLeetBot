# TeLeetBot
Telegram bot to track leetcode progress for groups of people

# Bot Commands
## Core
`/start`
- Where: DM
- Who: Anyone
- What: Intro + basic instructions.

`/link <leetcode_username>`
- Where: DM or Group
- Who: Anyone
- What: Links your Telegram account to your LeetCode handle and starts tracking from now (requires public LC profile).
- Usage: /link FluorescentPink

`/unlink`
- Where: DM
- Who: Anyone
- What: Unlinks your account and deletes your data (memberships, completions, last_seen). You can /link again later.

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

`.\.venv\Scripts\Activate.ps1`
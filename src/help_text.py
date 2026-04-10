def _telegram_compact_lines() -> list[str]:
    return [
        "<b>Command Overview</b>",
        "Tracks first-time accepted LeetCode solves, weekly scores, leaderboards, and optional solve announcements.",
        "",
        "<b>Getting Started</b>",
        "1. Link your account: <code>/link leetcode_username</code>",
        "2. In the group you want to join, run: <code>/join</code>",
        "3. View the current board: <code>/leaderboard</code>",
        "4. View your counts: <code>/stats</code>",
        "",
        "<b>High-Use Commands</b>",
        "<code>/relink leetcode_username</code> - repair your Telegram mapping if your Telegram account changed",
        "<code>/leave</code> - leave the current group's leaderboard",
        "<code>/unlink</code> - disconnect your LeetCode account",
        "<code>/uptime</code> - show how long the bot has been running",
        "<code>/postonsolve on|off</code> - toggle solve announcements for this group",
        "",
        "<b>Arguments</b>",
        "<code>leetcode_username</code> - your public LeetCode username",
        "<code>on|off</code> - enable or disable solve announcements",
    ]


def telegram_help_message(uptime: str, commands_only: bool = False) -> str:
    if not commands_only:
        return (
            "Hello! Link your LeetCode with /link leetcode_username. Then, in each group, "
            "use /join to begin showing your progress and enter the leaderboard.\n"
            "Use /help -c for a command overview.\n"
            f"Uptime: {uptime}"
        )

    lines = _telegram_compact_lines()
    lines.extend(["", f"<b>Uptime</b>: {uptime}"])
    return "\n".join(lines)


def discord_help_message() -> str:
    lines = [
        "**Command Overview**",
        "Tracks first-time accepted LeetCode solves, weekly scores, leaderboards, and optional solve announcements.",
        "",
        "**Getting Started**",
        "1. Link your account: `/link leetcode_username`",
        "2. In the channel you want to join, run: `/join`",
        "3. View the current board: `/leaderboard`",
        "4. View your counts: `/stats`",
        "",
        "**High-Use Commands**",
        "`/relink leetcode_username` - repair your Discord mapping if your Discord account changed",
        "`/leave` - leave the current channel leaderboard",
        "`/unlink` - disconnect your LeetCode account",
        "`/uptime` - show how long the bot has been running",
        "`/toggle_announcements on|off` - toggle solve announcements for this channel",
        "",
        "**Arguments**",
        "`leetcode_username` - your public LeetCode username",
        "`on|off` - enable or disable solve announcements",
        "",
        "Note: `/toggle_announcements` requires Manage Channels or Administrator.",
    ]
    return "\n".join(lines)

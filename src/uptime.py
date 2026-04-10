import time

START_TS = int(time.time())


def format_uptime(seconds: int) -> str:
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    mins, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if mins or hours or days:
        parts.append(f"{mins}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def current_uptime() -> str:
    return format_uptime(int(time.time()) - START_TS)

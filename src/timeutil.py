from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

def week_window_cst(now_utc:datetime) -> tuple[int,int]:
    # default: America/Chicago, Mon 00:00 -> next Mon 00:00
    tz = ZoneInfo("America/Chicago")
    local = now_utc.astimezone(tz)
    # Monday=0
    start_local = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=7)
    return int(start_local.astimezone(timezone.utc).timestamp()), int(end_local.astimezone(timezone.utc).timestamp())

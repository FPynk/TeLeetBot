from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# calculate start and end time for current week
def week_window_cst(now_utc:datetime) -> tuple[int,int]:
    # default: America/Chicago, Mon 00:00 -> next Mon 00:00
    tz = ZoneInfo("America/Chicago")
    # take input UTC timezone and convert into CST
    local = now_utc.astimezone(tz)
    # subtract now time with local.weekday() to get monday and zero out to get monday at 0,0,0,0
    # Monday=0
    start_local = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    # start + 7 days to get end
    end_local = start_local + timedelta(days=7)
    # convert and return as UTC
    return int(start_local.astimezone(timezone.utc).timestamp()), int(end_local.astimezone(timezone.utc).timestamp())

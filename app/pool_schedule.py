"""Pool schedule logic with regular hours and exception dates."""

from datetime import datetime, date, time
from typing import Optional

# Regular weekly schedule: day_of_week (0=Monday) -> list of (start_time, end_time) tuples
REGULAR_SCHEDULE = {
    0: [  # Monday
        (time(7, 0), time(8, 0)),
        (time(11, 0), time(13, 0)),
        (time(19, 30), time(22, 0)),
    ],
    1: [  # Tuesday
        (time(11, 0), time(13, 0)),
        (time(19, 30), time(22, 0)),
    ],
    2: [  # Wednesday
        (time(7, 0), time(8, 0)),
        (time(11, 0), time(13, 0)),
        (time(19, 30), time(22, 0)),
    ],
    3: [  # Thursday
        (time(11, 0), time(13, 0)),
        (time(19, 30), time(22, 0)),
    ],
    4: [  # Friday
        (time(7, 0), time(8, 0)),
        (time(11, 0), time(13, 0)),
        (time(19, 0), time(21, 0)),
    ],
    5: [],  # Saturday - CLOSED
    6: [  # Sunday
        (time(14, 0), time(17, 0)),
    ],
}

# Exception dates for 2025
# Format: date -> what's cancelled ("all", "midday", "evening")
EXCEPTIONS = {
    # No 11-1 PM swim
    date(2025, 2, 12): "midday",
    
    # No evening swim
    date(2025, 1, 16): "evening",
    date(2025, 1, 30): "evening",
    # Feb 12 already has midday cancelled, add evening too
    date(2025, 3, 6): "evening",
    
    # Closed all day
    date(2025, 1, 18): "all",
    date(2025, 2, 1): "all",
    date(2025, 2, 6): "all",
    date(2025, 2, 7): "all",
    date(2025, 2, 8): "all",
    date(2025, 2, 27): "all",
    date(2025, 2, 28): "all",
    date(2025, 3, 1): "all",
    date(2025, 3, 8): "all",
}

# Feb 12 has both midday and evening cancelled
EXCEPTIONS[date(2025, 2, 12)] = "midday_and_evening"

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def format_time(t: time) -> str:
    """Format time as 12-hour string."""
    hour = t.hour
    minute = t.minute
    am_pm = "AM" if hour < 12 else "PM"
    if hour == 0:
        hour = 12
    elif hour > 12:
        hour -= 12
    if minute == 0:
        return f"{hour}{am_pm}"
    return f"{hour}:{minute:02d}{am_pm}"


def format_session(start: time, end: time) -> str:
    """Format a session as a time range string."""
    return f"{format_time(start)}-{format_time(end)}"


def get_sessions_for_date(d: date) -> list[tuple[time, time]]:
    """Get pool sessions for a specific date, accounting for exceptions."""
    # Check if completely closed
    exception = EXCEPTIONS.get(d)
    if exception == "all":
        return []
    
    # Get regular schedule for this day of week
    sessions = REGULAR_SCHEDULE.get(d.weekday(), []).copy()
    
    if not sessions:
        return []
    
    # Filter based on exception type
    if exception == "midday":
        sessions = [s for s in sessions if not (s[0].hour == 11)]
    elif exception == "evening":
        sessions = [s for s in sessions if s[0].hour < 17]
    elif exception == "midday_and_evening":
        sessions = [s for s in sessions if s[0].hour < 11]
    
    return sessions


def is_pool_open_now(now: Optional[datetime] = None) -> tuple[bool, Optional[str]]:
    """
    Check if pool is currently open.
    Returns (is_open, current_session_end_time_str or None)
    """
    if now is None:
        now = datetime.now()
    
    current_time = now.time()
    sessions = get_sessions_for_date(now.date())
    
    for start, end in sessions:
        if start <= current_time <= end:
            return True, format_time(end)
    
    return False, None


def get_next_session(now: Optional[datetime] = None) -> Optional[dict]:
    """Get the next upcoming pool session (today or future)."""
    if now is None:
        now = datetime.now()
    
    current_time = now.time()
    current_date = now.date()
    
    # Check remaining sessions today
    sessions = get_sessions_for_date(current_date)
    for start, end in sessions:
        if start > current_time:
            return {
                "date": current_date,
                "day_name": "Today",
                "start": format_time(start),
                "end": format_time(end),
                "session_str": format_session(start, end),
            }
    
    # Check next 7 days
    for days_ahead in range(1, 8):
        future_date = date(current_date.year, current_date.month, current_date.day)
        try:
            future_date = date.fromordinal(current_date.toordinal() + days_ahead)
        except ValueError:
            continue
        
        sessions = get_sessions_for_date(future_date)
        if sessions:
            start, end = sessions[0]
            day_name = "Tomorrow" if days_ahead == 1 else DAY_NAMES[future_date.weekday()]
            return {
                "date": future_date,
                "day_name": day_name,
                "start": format_time(start),
                "end": format_time(end),
                "session_str": format_session(start, end),
            }
    
    return None


def get_pool_status(now: Optional[datetime] = None) -> dict:
    """Get complete pool status for display."""
    if now is None:
        now = datetime.now()
    
    is_open, closes_at = is_pool_open_now(now)
    sessions_today = get_sessions_for_date(now.date())
    next_session = get_next_session(now)
    
    # Format today's sessions
    today_sessions_str = []
    current_time = now.time()
    for start, end in sessions_today:
        session_str = format_session(start, end)
        if start <= current_time <= end:
            status = "now"
        elif end < current_time:
            status = "past"
        else:
            status = "upcoming"
        today_sessions_str.append({"time": session_str, "status": status})
    
    # Check for exception message
    exception = EXCEPTIONS.get(now.date())
    exception_msg = None
    if exception == "all":
        exception_msg = "Closed today (scheduled closure)"
    elif exception == "midday":
        exception_msg = "No 11AM-1PM session today"
    elif exception == "evening":
        exception_msg = "No evening session today"
    elif exception == "midday_and_evening":
        exception_msg = "Only morning session today"
    
    return {
        "is_open": is_open,
        "closes_at": closes_at,
        "day_name": DAY_NAMES[now.weekday()],
        "sessions_today": today_sessions_str,
        "is_closed_today": len(sessions_today) == 0,
        "next_session": next_session,
        "exception_msg": exception_msg,
    }


def get_weekly_schedule() -> list[dict]:
    """Get the regular weekly schedule for display."""
    schedule = []
    for day_idx, day_name in enumerate(DAY_NAMES):
        sessions = REGULAR_SCHEDULE.get(day_idx, [])
        if sessions:
            sessions_str = ", ".join(format_session(s, e) for s, e in sessions)
        else:
            sessions_str = "CLOSED"
        schedule.append({"day": day_name, "sessions": sessions_str})
    return schedule

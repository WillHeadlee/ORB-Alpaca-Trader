"""Eastern Time helpers and market-hours utilities."""

from datetime import datetime, time
import pytz

ET = pytz.timezone("America/New_York")

MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)


def now_et() -> datetime:
    return datetime.now(ET)


def to_et(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return ET.localize(dt)
    return dt.astimezone(ET)


def is_market_open(dt: datetime | None = None) -> bool:
    dt = to_et(dt) if dt else now_et()
    t = dt.time()
    return MARKET_OPEN <= t < MARKET_CLOSE and dt.weekday() < 5


def opening_range_end(opening_range_minutes: int, dt: datetime | None = None) -> datetime:
    """Return the ET datetime when the opening range observation window closes."""
    base = to_et(dt) if dt else now_et()
    market_open_today = ET.localize(
        datetime(base.year, base.month, base.day, 9, 30)
    )
    from datetime import timedelta
    return market_open_today + timedelta(minutes=opening_range_minutes)


def hard_close_dt(hard_close_time: str, dt: datetime | None = None) -> datetime:
    """Parse 'HH:MM' and return today's hard-close datetime in ET."""
    base = to_et(dt) if dt else now_et()
    hh, mm = map(int, hard_close_time.split(":"))
    return ET.localize(datetime(base.year, base.month, base.day, hh, mm))


def seconds_until(target: datetime) -> float:
    delta = target - now_et()
    return max(delta.total_seconds(), 0.0)


def next_market_open() -> datetime:
    """Return the next 9:30 AM ET on a weekday (today if we're pre-market)."""
    from datetime import timedelta
    now = now_et()
    candidate = ET.localize(datetime(now.year, now.month, now.day, 9, 30))
    # If we're already past 9:30 today, advance to next day
    if now >= candidate:
        candidate += timedelta(days=1)
    # Skip weekends
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate


async def wait_until_market_open() -> None:
    """Sleep until the next 9:30 AM ET open, logging a countdown."""
    import asyncio
    target = next_market_open()
    secs = seconds_until(target)
    if secs > 0:
        import logging
        log = logging.getLogger("orb_trader")
        log.info(
            f"Market closed. Waiting {secs/3600:.1f}h until "
            f"{target.strftime('%Y-%m-%d %H:%M')} ET"
        )
        await asyncio.sleep(secs)

import re
from datetime import datetime


# BOT_TIMEZONE = timezone(timedelta(hours=3))

def get_now():
    #return datetime.now(BOT_TIMEZONE)
    return datetime.now()


def to_datetime(string_time: str) -> datetime:
    return datetime.strptime(string_time, "%Y-%m-%d %H:%M:%S")


def to_string(datetime_time: datetime) -> str:
    return datetime_time.strftime("%Y-%m-%d %H:%M:%S")


def format_time(time: datetime | int) -> str:
    if isinstance(time, datetime):
        hours = time.hour
        minutes = time.minute
        seconds = time.second

    else:
        hours = time // 3600
        minutes = (time // 60) % 60
        seconds = time % 60

    ret = f"{f'{str(hours)}ч ' if hours >= 1 else ''}" \
    f"{f'{str(minutes)}м ' if minutes >= 1 else ''}" \
    f"{f'{str(seconds)}с' if seconds >= 1 else ''}"

    return ret


def duration_seconds_from_string(time_str: str) -> int:
    time_str = time_str.strip().lower()

    hours = 0
    minutes = 0

    h_match = re.search(r"(\d+)\s*(h|ч)", time_str)
    m_match = re.search(r"(\d+)\s*(m|м)", time_str)

    if h_match:
        hours = int(h_match.group(1))
    if m_match:
        minutes = int(m_match.group(1))

    return hours * 60 * 60 + minutes * 60


def format_without_date(time: datetime):
    return datetime.strftime(time, "%H:%M:%S")
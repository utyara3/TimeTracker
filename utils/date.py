from datetime import datetime, timezone, timedelta


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

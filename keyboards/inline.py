import calendar as calendar_lib
from datetime import datetime, timedelta

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from utils import date


def rate_keyboard(time_session_id: int) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()

    for num in range(1, 6):
        builder.add(
            InlineKeyboardButton(
                text=str(num),
                callback_data=f"rate_time_session:{time_session_id}:{num}"
            )
        )

    return builder


def pagination_date_kb(info: str, current_day: datetime.date) -> InlineKeyboardBuilder:
    today = date.get_now()
    
    yesterday = current_day - timedelta(days=1)
    tomorrow = current_day + timedelta(days=1)
    
    buttons = []
    buttons.append(
        InlineKeyboardButton(
            text=f"{yesterday.day} ←",
            callback_data=f"{info}:{yesterday}"
        )
    )
    buttons.append(
        InlineKeyboardButton(
            text=f"{current_day.day}/{current_day.month}",
            callback_data=f"{info}:{current_day}:edit"
        ),
    )
    if current_day.day != today.day:
        buttons.append(
            InlineKeyboardButton(
                text=f"→ {tomorrow.day}",
                callback_data=f"{info}:{tomorrow}"
            ),
        )

    builder = InlineKeyboardBuilder()
    builder.row(*buttons)

    return builder


def calendar_kb(
    info: str,
    year: int,
    month: int,
    active_days: set[int] | None = None
) -> InlineKeyboardBuilder:
    today = date.get_now().date()
    active_days = active_days or set()

    builder = InlineKeyboardBuilder()

    prev_year, prev_month = date.shift_month(year, month, -1)
    next_year, next_month = date.shift_month(year, month, 1)

    header = [
        InlineKeyboardButton(
            text="◀️",
            callback_data=f"calendar:{info}:month:{prev_year}-{prev_month:02d}"
        ),
        InlineKeyboardButton(
            text=f"{date.MONTH_NAMES[month - 1]} {year}",
            callback_data=f"calendar:{info}:noop"
        ),
    ]

    if (year, month) < (today.year, today.month):
        header.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=f"calendar:{info}:month:{next_year}-{next_month:02d}"
            )
        )

    builder.row(*header)

    builder.row(*[
        InlineKeyboardButton(text=day_name, callback_data=f"calendar:{info}:noop")
        for day_name in date.WEEKDAY_NAMES
    ])

    for week in calendar_lib.monthcalendar(year, month):
        day_buttons = []
        for day in week:
            if day == 0:
                day_buttons.append(
                    InlineKeyboardButton(text=" ", callback_data=f"calendar:{info}:noop")
                )
                continue

            mark = "•" if day in active_days else ""
            day_buttons.append(
                InlineKeyboardButton(
                    text=f"{day}{mark}",
                    callback_data=f"calendar:{info}:day:{year}-{month:02d}-{day:02d}"
                )
            )

        builder.row(*day_buttons)

    if today.month != month or today.year != year:
        builder.row(
            InlineKeyboardButton(
                text="📍 Сегодня",
                callback_data=f"calendar:{info}:today"
            )
        )

    return builder

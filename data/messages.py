from utils import date
from datetime import datetime, timedelta


def format_switch_state_message(
    prev_state: str,
    new_state: str,
    prev_tag: str,
    new_tag: str,
    delta_time: str
) -> str:
    return f"""✨ <b>Смена состояния успешна!</b>

<b>Было:</b> {DEFAULT_STATES[prev_state][1]} <code>{prev_state}</code> <code>{prev_tag if prev_tag else ''}</code>
<b>Стало:</b> {DEFAULT_STATES[new_state][1]} <code>{new_state}</code> <code>{new_tag if new_tag else ''}</code>

🕐 <b>Интервал:</b> <i>{delta_time}</i>"""


def old_format_states_history(states: list[dict]) -> str:
    if not states:
        return "📭 История состояний за сегодня пуста"

    ret_str = "📊 <b>История состояний сегодня:</b>\n\n"

    for i, state in enumerate(states):
        state_name = state["state_name"]
        start_time = date.format_time_hhmm(state['start_time'])
        if state['end_time']:
            end_time = date.format_time_hhmm(state['end_time'])
        else:
            end_time = "now"

        duration_seconds = date.calculate_duration_seconds(
            start_time=state['start_time'],
            end_time=state.get('end_time'),
            duration_seconds=state.get("duration_seconds")
        )
        mood = state.get("mood")
        tag = state.get("tag", "")

        if duration_seconds:
            duration_str = date.format_time(duration_seconds)
        else:
            duration_str = "Активно"

        mood_str = ""
        if 'Активно' not in duration_str:
            mood_str = " | " + ("⭐" * mood if mood else "❌")

        tag_str = " " * 4 + f"🏷️ {tag}\n" if tag else ""

        divide = "——————" if i < len(states) - 1 else ""

        ret_str += f"""{"🔸" if i == 0 else "🔹"} <b>{state_name}</b>
    ⏱️ {start_time} - {end_time}
    ⏳ {duration_str} {mood_str}
{tag_str} {divide}\n\n"""

    return ret_str


def format_states_history(
    states: list[dict],
    target_day: datetime.date | None = None
) -> str:
    if not states:
        return "📭 История состояний за этот день пуста"

    if target_day is None:
        target_day = date.to_datetime(states[0]['start_time']).date()

    is_today = target_day == date.get_now().date()
    day_end_label = date.format_time_hhmm(date.day_boundary(target_day))

    day_label = "сегодня" if is_today else target_day.strftime("%d.%m.%Y")
    weekday = date.WEEKDAY_NAMES[target_day.weekday()]

    ret_str = f"🗂 <b>История за {day_label} ({weekday})</b>\n\n"

    # reversed(): в БД порядок от новой сессии к старой,
    # а история дня рассказывается с первой сессии до последней
    for state in reversed(states):
        state_name = state["state_name"]
        start_time = date.format_time_hhmm(state['start_time'])
        if state['end_time']:
            end_time = date.format_time_hhmm(state['end_time'])
        elif is_today:
            end_time = "now"
        else:
            # незакрытая сессия на прошедшем дне — обрезана по границе суток
            end_time = day_end_label

        duration_seconds = date.day_scoped_duration_seconds(
            start_time=state['start_time'],
            end_time=state.get('end_time'),
            duration_seconds=state.get("duration_seconds"),
            target_day=target_day
        )
        mood = state.get("mood")
        tag = state.get("tag", "")

        duration_str = date.format_time(duration_seconds)

        mood_str = "| " + ("*" * mood if mood else "#")

        tag_str = f" | 🏷️ {tag}" if tag else ""
        
        ret_str += f"""<b>{state_name}</b> {tag_str}
{start_time} - {end_time} | {duration_str} {mood_str}\n\n"""
    
    return ret_str


MONTH_CALENDAR_TITLES = {
    "date_history": "🗂 Выберите день, чтобы посмотреть историю состояний",
    "date_statistics": "📊 Выберите день, чтобы посмотреть статистику",
}


def format_month_calendar(info: str, year: int, month: int) -> str:
    title = MONTH_CALENDAR_TITLES.get(info, "📅 Выберите день")
    month_name = date.MONTH_NAMES[month - 1]

    return f"""🗓 <b>{month_name} {year}</b>

{title}
📍 Дни с записями отмечены •"""


def format_empty_day(day: datetime.date) -> str:
    return f"📭 <b>Нет состояний за {day.strftime('%d.%m.%Y')}.</b>"


def format_choose_state(day: datetime.date) -> str:
    weekday = date.WEEKDAY_NAMES[day.weekday()]
    return f"ℹ️ Выберите состояние за {day.strftime('%d.%m.%Y')} ({weekday}):"


def format_commands() -> str:
    ret = ""
    for en, ru in DEFAULT_STATES.items():
        ret += f"{ru[1]} <code>/{en}</code> - <b>{ru[0]}</b>\n"

    return ret


def format_user_statistics(
    target_date: str,
    current_state_name: str,
    current_state_tag: str,
    delta_time: dict[str, int],
    state_count: int,
    chronology: str,
    states_in_precents: dict[str, list],
    productivity: int,
    longest_total: dict[str, str],
    shortest_total: dict[str, str],
    longest_session: dict[str, str],
    shortest_session: dict[str, str],
    average_session: str
) -> str:
    current_state = f"<code>{current_state_name}</code>"
    current_state += f"  (🏷️ <code>{current_state_tag}</code>)" if current_state_tag else ""

    hours, minutes, seconds = delta_time.values()
    duration = ""
    if hours >= 1:
        duration += f"{hours}ч "
    if minutes >= 1:
        duration += f"{minutes}м "
    if seconds >= 1:
        duration += f"{seconds}с"

    ratio = ""
    for state_name, state_duration in sorted(
            states_in_precents.items(),
            key=lambda state: state[1][0],
            reverse=True
    ):
        formatted_duration = date.format_time(state_duration[0])
        duration_percents = state_duration[1]

        bars_count = int(duration_percents / 10)
        bar = "█" * bars_count + "░" * (10 - bars_count)

        ratio += (" " * 4 + f"· {DEFAULT_STATES[state_name][1]} "
                            f"{state_name}: <b>{duration_percents}%</b> "
                  f"({formatted_duration})\n" + " "*4 + f"{bar}\n")

    return f"""📊 <b>Статистика состояний {target_date}:</b>

🎯 <b>Последнее:</b>
    📍 <b>Состояние:</b> {current_state}
    ⌛ <b>Длится:</b> {duration}

📈 <b>Активность:</b>
    🔢 <b>Сессий:</b> {state_count}
    🎞️ <b>Хронология:</b> {chronology}

📐 <b>Распределение:</b>
{ratio}
🏆 <b>Рекорды:</b>
    🥇 <b>Самые долгие:</b>
        📦 По сумме: {longest_total['name']} ({longest_total['duration']})
        ⏱️ Единичная: {longest_session['name']} ({longest_session['duration']})

    ⚡ <b>Самые быстрые:</b>
        📦 По сумме: {shortest_total['name']} ({shortest_total['duration']})
        ⏱️ Единичная: {shortest_session['name']} ({shortest_session['duration']})
        
📊 <b>Эффективность:</b>
    ⏱️ <b>Средняя сессия:</b> {average_session}
    📊 <b>Продуктивность:</b> {productivity}%
"""


def format_fix_cmd(
    state_name: str,
    state_start_time: str,
    new_state: str,
    prev_state_end_time: str
):
    return f"""✨ <b>Состояние было успешно разеделено!</b>
    
<b>Текущее:</b> <code>{new_state}</code> <code>{prev_state_end_time} - сейчас</code>
<b>Прошлое:</b> <code>{state_name}</code> <code>{state_start_time} - {prev_state_end_time}</code>
"""


def format_state_info(state_info: dict) -> str:
    start_time = date.format_time_hhmm(state_info['start_time'])
    end_time = date.format_time_hhmm(state_info['end_time'])
    duration = state_info['duration_seconds']

    duration_dict = {
        "hours": duration//3600,
        "minutes": (duration//60)%60,
        "seconds": duration % 60
    }

    duration_str = f"{duration_dict['hours']}ч " if duration_dict['hours'] else ""
    duration_str += f"{duration_dict['minutes']}м " if duration_dict['minutes'] else ""
    duration_str += f"{duration_dict['seconds']}с" if duration_dict['seconds'] else ""

    ret = f"""📍 <b>Состояние</b> <code>{state_info['name']}</code>

📋 <b>Тег:</b> <code>{state_info['tag'] or 'отсутствует'}</code>
🕐 <b>Время:</b> {start_time}-{end_time}
⏱️ <b>Длительность:</b> {duration_str}
✨ <b>Оценка:</b> <code>{state_info['mood'] or '?'}/5</code>
    """

    return ret


def format_predict_next_state(next_state: list, predict_by: str) -> str:
    ret_str = f"✨ <b>Предсказываю следующее состояние...</b>\n"
    ret_str += f"\n⚙️ <b>Паттерн:</b> <i>{predict_by}</i>\n"
    ret_str += f"\n📍 <b>Распределение вероятностей:</b>"
    for i in range(len(next_state)):
        ret_str += f"\n-  {DEFAULT_STATES[next_state[i][0]][1]} " \
        f"<code>{next_state[i][0]}</code> (<b><i>{next_state[i][1]}%</i></b>)"

    return ret_str



DEFAULT_STATES = {
    "study": ["учеба", "📚"],
    "work": ["работа", "💼"],
    "chill": ["отдых", "🏖"],
    "sleep": ["сон", "💤"],
    "wait": ["ожидание", "🕰"],
    "other": ["другое", "📌"],
    "stop": ["не учитывать", "⏹️"]
}

COMMON = {
    'start_cmd':"👋 <b>Привет! Это бот для трекинга времени.</b>\n\n"
                "📊 Используй команды для отслеживания своей активности: /work, /study, /sleep, /stop\n\n"
                "🔎 Чтобы увидеть полный перечень состояний, воспользуйся командой /help",
    'cancel_cmd': "❌ <b>Действие отменено</b>",
    'help_cmd': f"""ℹ️ <b>Помощь по командам:</b>\n{format_commands()}
📊 <code>/stats</code> - статистика
📜 <code>/history</code> - история состояний
🏷️ <code>/my_tags</code> - ваши теги
🛠 <code>/fix</code> <i>время состояние [тег]</i> - исправить забытое переключение

<b>Пример <code>/fix</code>:</b>
<code>/fix 1ч 10м study математика</code>
→ Добавит учёбу с момента "1 час 10 минут назад" до сейчас

💡 Обычно просто: <code>/состояние [тег]</code>""",
    'rate_old_state': "⭐ <b>Оцените прошлое состояние:</b>",
    'states_message': f"""ℹ️ <b>Выберите состояние:</b>\n
{format_commands()}
Вы также можете установить тег состоянию, написав его после названия состояния:
<code>/состояние тег</code>
""",
    'choose_state_to_change': "ℹ️ Выберите состояние:",
    "state_name_changed": "✅ <b>Состояние было успешно изменено!</b>",
    "state_tag_changed": "✅ <b>Тег состояния был успешно изменен!</b>",
    "state_mood_changed": "✅ <b>Оценка состояния была успешно изменена!</b>",
    "choose_new_state": "ℹ️ Выберите новое состояние:",
    "enter_new_tag": "ℹ️ Введите новый тег:",
    "rate_state": "⭐ <b>Оцените состояние:</b>",
}

SUCCESS = {
    'state_change': "✅ <b>Состояние было изменено!</b>",
    "state_tag_deleted": "✅ <b>Тег состояния был успешно удален!</b>",
    'state_rated': "⭐ <b>Оценка сохранена!</b>"
}

FAILURE = {
    'state_change': "❌ <b>Состояние не было изменено!</b>",
    'have_not_tags': """❌ <b>У вас пока что нет тегов.</b>\n
Вы можете установить тег состоянию, написав его после названия состояния:
<code>/состояние тег</code>""",
    'no_states_today': "❌ <b>У вас нет состояний сегодня.</b>",
    "wrong_args": "❌ <b>Команда была использована неправильно.</b>",
    "fix_wrong_time": "❌ <b>Время команды некорректное.</b>",
    "few_days": "❌ <b>Вы пользуетесь ботом слишком мало. Эта функция не доступна.</b>"
}

REPLY_KB = {
    'start_kb': {
        'set_state': '🎯 Установить состояние',
        'statistics': '📊 Статистика',
        'history': '🗂 История состояний'
    }
}

from utils import date
from datetime import datetime


def format_switch_state_message(
    prev_state: str,
    new_state: str,
    prev_tag: str,
    new_tag: str,
    delta_time: str
) -> str:
    return f"""✨ <b>Смена состояния успешна!</b>

▫️ <b>Было:</b> <code>{prev_state}</code> <code>{prev_tag if prev_tag else ''}</code>
▫️ <b>Стало:</b> <code>{new_state}</code> <code>{new_tag if new_tag else ''}</code>

🕐 <b>Интервал:</b> <i>{delta_time}</i>"""


def format_states_history(states: list[dict]) -> str:
    if not states:
        return "📭 История состояний за сегодня пуста"

    ret_str = "📊 <b>История состояний сегодня:</b>\n\n"

    for i, state in enumerate(states):
        state_name = state["state_name"]
        start_time = datetime.strftime(
            date.to_datetime(state['start_time']),
            "%H:%M"
        )
        if state['end_time']:
            end_time = datetime.strftime(
                date.to_datetime(state['end_time']),
                "%H:%M"
            )
        else:
            end_time = "now"

        duration_seconds = state.get("duration_seconds", 0)
        mood = state.get("mood")
        tag = state.get("tag", "")

        if duration_seconds:
            # hours = duration_seconds // 3600
            # minutes = (duration_seconds // 60) % 60
            # seconds = duration_seconds % 60
            # duration_str = f"{f'{str(hours)}ч ' if hours >= 1 else ''}" \
            #                f"{f'{str(minutes)}м ' if minutes >= 1 else ''}" \
            #                f"{f'{str(seconds)}с' if seconds >= 1 else ''}"
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


def format_commands() -> str:
    ret = ""
    for en, ru in DEFAULT_STATES.items():
        ret += f"{ru[1]} <code>/{en}</code> - {ru[0]}\n"

    return ret


def format_user_statistics(
    current_state_name: str,
    current_state_tag: str,
    delta_today_dict: dict[str, int],
    state_count_today: int,
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

    hours, minutes, seconds = delta_today_dict.values()
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

    return f"""📊 <b>Статистика состояний за сегодня:</b>

🎯 <b>Текущее:</b>
    📍 <b>Состояние:</b> {current_state}
    ⌛ <b>Длится:</b> {duration}

📈 <b>Активность:</b>
    🔢 <b>Сессий:</b> {state_count_today}
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


DEFAULT_STATES = {
    "study": ["учеба", "📚"],
    "work": ["работа", "💼"],
    "chill": ["отдых", "🏖"],
    "sleep": ["сон", "💤"],
    "wait": ["ожидание", "🕰"],
    "other": ["другое", "💊"],
    "stop": ["не учитывать", "⏹️"]
}

COMMON = {
    'start_cmd':"👋 <b>Привет! Это бот для трекинга времени.</b>\n\n"
                "📊 Используй команды для отслеживания своей активности: /work, /study, /sleep, /stop\n\n"
                "🔎 Чтобы увидеть полный перечень состояний, воспользуйся командой /help",
    'cancel_cmd': "❌ <b>Действия были отменены. Состояние сброшено.</b>",
    'help_cmd': f"""ℹ️ <b>Помощь по командам:</b>\n{format_commands()}
📊 /stats - статистика
🏷️ /my_tags - ваши теги""",
    'rate_state': "⭐ <b>Оцените прошлое состояние:</b>",
    'states_message': f"""ℹ️ <b>Выберите состояние:</b>\n
{format_commands()}
Вы также можете установить тег состоянию, написав его после названия состояния:
<code>/состояние тег</code>
"""
}

SUCCESS = {
    'state_change': "✅ <b>Состояние было изменено!</b>",
    'state_rated': "⭐ <b>Оценка сохранена!</b>"
}

FAILURE = {
    'state_change': "❌ <b>Состояние не было изменено!</b>",
    'have_not_tags': """❌ <b>У вас пока что нет тегов.</b>\n
Вы можете установить тег состоянию, написав его после названия состояния:
<code>/состояние тег</code>""",
    'no_states_today': "❌ <b>У вас нет состояний сегодня.</b>"
}

REPLY_KB = {
    'start_kb': {
        'set_state': '🎯 Установить состояние',
        'statistics': '📊 Статистика',
        'history': '🗂 История состояний'
    }
}

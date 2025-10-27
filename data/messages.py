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
        return "📭 История состояний пуста"

    ret_str = "📊 <b>История состояний:</b>\n\n"

    for i, state in enumerate(states):
        state_name = state["state_name"]
        duration_seconds = state.get("duration_seconds", 0)
        mood = state.get("mood")
        tag = state.get("tag", "")

        if duration_seconds:
            hours = duration_seconds // 3600
            minutes = (duration_seconds // 60) % 60
            seconds = duration_seconds % 60
            duration_str = f"{f'{str(hours)}ч ' if hours >= 1 else ''}" \
                           f"{f'{str(minutes)}м ' if minutes >= 1 else ''}" \
                           f"{f'{str(seconds)}с' if seconds >= 1 else ''}"
        else:
            duration_str = "⏳ Активно"

        mood_str = ""
        if 'Активно' not in duration_str:
            mood_str = " | " + ("⭐" * mood if mood else "❌")

        tag_str = f"   🏷️ {tag}\n" if tag else ""

        divide = "——————" if i < len(states) - 1 else ""

        ret_str += f"""{"🔸" if i == 0 else "🔹"} <b>{state_name}</b>
   ⏱️ {duration_str} {mood_str}
{tag_str} {divide}\n\n"""

    return ret_str


def format_commands() -> str:
    ret = ""
    for en, ru in DEFAULT_STATES.items():
        ret += f"{ru[1]} <code>/{en}</code> - {ru[0]}\n"

    return ret


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
<code>/состояние тег</code>"""
}

REPLY_KB = {
    'start_kb': {
        'set_state': '🎯 Установить состояние',
        'statistics': '📊 Статистика',
        'history': '🗂 История состояний'
    }
}

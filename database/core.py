import aiosqlite
from datetime import datetime, timedelta

from aiogram.types import Message

from config import USERS_DB_PATH
from data.messages import DEFAULT_STATES
from utils import date


async def init_db():
    async with aiosqlite.connect(USERS_DB_PATH) as conn:
        await conn.execute('PRAGMA foreign_keys = ON')
        await conn.execute('PRAGMA journal_mode=WAL')
        await conn.execute('PRAGMA synchronous=NORMAL')
        await conn.execute('PRAGMA busy_timeout=10000')

        cursor = await conn.cursor()


        await cursor.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            full_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

        await cursor.execute("""CREATE TABLE IF NOT EXISTS states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )""")

        await cursor.execute("""CREATE TABLE IF NOT EXISTS time_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            state_id INTEGER NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            tag TEXT,
            duration_seconds INTEGER,
            mood INTEGER CHECK (mood >= 1 AND mood <= 5),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (state_id) REFERENCES states(id) ON DELETE CASCADE
        )""")

        await cursor.executemany(
            "INSERT OR IGNORE INTO states (name) VALUES (?)",
            [(state, ) for state in DEFAULT_STATES]
        )

        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_tg_id ON users (tg_id)")
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_states_name ON states (name)")
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON time_sessions (user_id)")
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_state_id ON time_sessions (state_id)")
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON time_sessions (start_time)")
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_end_time ON time_sessions (end_time)")

        await conn.commit()


async def is_user_in_database(
    message: Message | None = None,
    tg_id: int | None = None
) -> bool:
    if message is not None:
        tg_id = message.from_user.id

    async with aiosqlite.connect(USERS_DB_PATH) as conn:
        async with conn.execute("SELECT 1 FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            return await cursor.fetchone() is not None


async def get_state_id_by_name(state_name: str) -> int | None:
    async with aiosqlite.connect(USERS_DB_PATH) as conn:
        cursor = await conn.execute("SELECT id FROM states WHERE name = ?", (state_name,))
        res = await cursor.fetchone()

        return res[0] if res else None


async def get_user_states(
    message: Message | None = None,
    tg_id: int | None = None,
    limit: int = -1
) -> list[dict[str, str]] | None:
    if message is not None:
        tg_id = message.from_user.id

    user_id = await get_user_id_by_tg_id(tg_id=tg_id)

    async with aiosqlite.connect(USERS_DB_PATH) as conn:
        cursor = await conn.execute("""
            SELECT ts.*, s.name as state_name
            FROM time_sessions ts
            JOIN states s ON ts.state_id = s.id
            WHERE ts.user_id = ?
            ORDER BY ts.start_time DESC
            LIMIT ?
        """, (user_id, limit))

        states = await cursor.fetchall()

        if not states:
            return None

        columns = [description[0] for description in cursor.description]

        # 'id', 'user_id', 'state_id', 'start_time', 'end_time',
        # 'tag', 'duration_seconds', 'mood', 'state_name'
        return [dict(zip(columns, state)) for state in states]


async def get_current_state(
    message: Message | None = None,
    tg_id: int | None = None
) -> dict[str, str] | None:
    states = await get_user_states(
        message=message,
        tg_id=tg_id,
        limit=1
    )

    if states is None:
        return None

    state = states[0]

    if state['end_time'] is None:
        return state

    return None


async def get_user_id_by_tg_id(
    message: Message | None = None,
    tg_id: int | None = None
) -> int | None:
    if message is not None:
        tg_id = message.from_user.id

    async with aiosqlite.connect(USERS_DB_PATH) as conn:
        cursor = await conn.execute('SELECT id FROM users WHERE tg_id = ?', (tg_id,))
        res = await cursor.fetchone()

        return res[0] if res else None


async def get_user_tags(
    message: Message | None = None,
    tg_id: int | None = None
) -> list[str] | None:
    if message is not None:
        tg_id = message.from_user.id

    user_id = await get_user_id_by_tg_id(tg_id=tg_id)

    async with aiosqlite.connect(USERS_DB_PATH) as conn:
        cursor = await conn.execute("SELECT tag FROM time_sessions WHERE user_id = ?", (user_id, ))
        tags = await cursor.fetchall()

        return [tag[0] for tag in tags if tag[0]]


async def add_user_to_database(
    message: Message | None = None,
    tg_id: int | None = None,
    username: str = "",
    fullname: str | None = None,
) -> None:
    if message is not None:
        tg_id = message.from_user.id
        username = message.from_user.username or ""
        fullname = message.from_user.full_name

    async with aiosqlite.connect(USERS_DB_PATH) as conn:
        await conn.execute(
            "INSERT OR IGNORE INTO users (tg_id, username, full_name) VALUES (?, ?, ?)",
            (tg_id, username, fullname)
        )

        await conn.commit()


async def end_session(user_id: int, conn) -> None:
    cursor = await conn.execute("""
        SELECT start_time FROM time_sessions 
        WHERE user_id = ? AND end_time IS NULL
    """, (user_id,))
    result = await cursor.fetchone()

    if not result:
        return

    start_time_str = result[0]
    start_time = date.to_datetime(start_time_str)
    end_time = date.get_now()

    duration_seconds = int((end_time - start_time).total_seconds())

    await conn.execute("""
        UPDATE time_sessions 
        SET end_time = ?, duration_seconds = ?
        WHERE user_id = ? AND end_time IS NULL
    """, (date.to_string(end_time), duration_seconds, user_id))


async def switch_state(
    message: Message | None = None,
    tg_id: int | None = None,
    new_state: str = "other",
    tag: str = ""
) -> dict[str, str] | bool:
    if message is not None:
        tg_id = message.from_user.id

    user_id = await get_user_id_by_tg_id(tg_id=tg_id)
    if not user_id:
        return False

    prev_state_data = await get_current_state(tg_id=tg_id)
    prev_state_name = prev_state_data.get('state_name', '') if prev_state_data else None
    prev_state_start_time = prev_state_data.get('start_time', 0) if prev_state_data else None
    prev_state_tag = prev_state_data.get('tag', '') if prev_state_data else None
    prev_state_time_session_id = prev_state_data.get('id', '') \
        if prev_state_data else None

    state_id = await get_state_id_by_name(state_name=new_state)
    if not state_id:
        return False

    ret_dict = {
        "previous_state": prev_state_name,
        "start_time": prev_state_start_time,
        "new_state": new_state,
        "prev_tag": prev_state_tag,
        "new_tag": tag,
        "time_session_id": prev_state_time_session_id,
    }

    async with aiosqlite.connect(USERS_DB_PATH) as conn:
        await end_session(user_id, conn)

        current_time = date.to_string(date.get_now())

        await conn.execute("""
            INSERT INTO time_sessions (user_id, state_id, start_time, tag) VALUES (?, ?, ?, ?)
        """, (user_id, state_id, current_time, tag))

        await conn.commit()

        return ret_dict


async def rate_state(time_session_id: int, mood: int) -> None:
    async with aiosqlite.connect(USERS_DB_PATH) as conn:
        await conn.execute("""
            UPDATE time_sessions SET mood = ? 
            WHERE id = ?
        """, (mood, time_session_id))

        await conn.commit()


async def fix_states(
    first_state_end_time: datetime,
    first_state_duration_seconds: int,
    new_state: str,
    new_tag: str,
    message: Message | None = None,
    tg_id: int | None = None,
) -> bool:
    if message is not None:
        tg_id = message.from_user.id

    user_id = await get_user_id_by_tg_id(tg_id=tg_id)
    if not user_id:
        return False

    state_id = await get_state_id_by_name(state_name=new_state)
    if not state_id:
        return False

    async with aiosqlite.connect(USERS_DB_PATH) as conn:
        await conn.execute("""
            UPDATE time_sessions 
            SET end_time = ?, duration_seconds = ?
            WHERE user_id = ? AND end_time IS NULL
        """, (first_state_end_time, first_state_duration_seconds, user_id))

        await conn.execute("""
            INSERT INTO time_sessions (user_id, state_id, start_time, tag) 
            VALUES (?, ?, ?, ?)
        """, (user_id, state_id, first_state_end_time, new_tag))

        await conn.commit()
            
        
    return True
        



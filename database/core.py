import aiosqlite

from config import USERS_DB_PATH, DEFAULT_STATES


async def init_db():
    async with aiosqlite.connect(USERS_DB_PATH) as conn:
        await conn.execute('PRAGMA foreign_keys = ON')

        cursor = await conn.cursor()


        await cursor.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER UNIQUE NOT NULL,
            username TEXT NOT NULL,
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
            notes TEXT,
            duration_minutes INTEGER,
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
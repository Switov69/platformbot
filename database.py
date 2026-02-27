import aiosqlite
from datetime import datetime

DB_PATH = 'platform.db'

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                nickname TEXT NOT NULL,
                citizenship TEXT NOT NULL,
                bank_account TEXT NOT NULL,
                completed_jobs INTEGER DEFAULT 0,
                total_earned REAL DEFAULT 0.0,
                registration_date DATETIME
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS vacancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                priority TEXT NOT NULL,
                category TEXT NOT NULL,
                salary REAL NOT NULL,
                status TEXT DEFAULT 'not_completed',
                assigned_user_id INTEGER DEFAULT NULL,
                created_by_id INTEGER DEFAULT NULL,
                coords TEXT DEFAULT NULL,
                channel_message_id INTEGER DEFAULT NULL,
                created_at DATETIME
            )
        ''')
        await db.commit()

class DB:
    @staticmethod
    async def get_user(user_id):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            return await cursor.fetchone()

    @staticmethod
    async def register_user(user_id, nickname, citizenship, bank_account):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (id, nickname, citizenship, bank_account, registration_date) VALUES (?, ?, ?, ?, ?)",
                (user_id, nickname, citizenship, bank_account, datetime.now())
            )
            await db.commit()

    @staticmethod
    async def update_user_bank(user_id, new_bank):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET bank_account = ? WHERE id = ?", (new_bank, user_id))
            await db.commit()

    @staticmethod
    async def add_vacancy(desc, priority, category, salary, creator_id):
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "INSERT INTO vacancies (description, priority, category, salary, created_by_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (desc, priority, category, salary, creator_id, datetime.now())
            )
            v_id = cursor.lastrowid
            await db.commit()
            return v_id

    @staticmethod
    async def get_vacancy_by_id(v_id):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM vacancies WHERE id = ?", (v_id,))
            return await cursor.fetchone()

    @staticmethod
    async def assign_vacancy(v_id, user_id):
        async with aiosqlite.connect(DB_PATH) as db:
            status = 'in_progress' if user_id else 'not_completed'
            await db.execute(
                "UPDATE vacancies SET assigned_user_id = ?, status = ? WHERE id = ?",
                (user_id, status, v_id)
            )
            await db.commit()

    @staticmethod
    async def update_vacancy_status(v_id, status, coords=None):
        async with aiosqlite.connect(DB_PATH) as db:
            if coords:
                await db.execute("UPDATE vacancies SET status = ?, coords = ? WHERE id = ?", (status, coords, v_id))
            else:
                await db.execute("UPDATE vacancies SET status = ? WHERE id = ?", (status, v_id))
            await db.commit()

    @staticmethod
    async def update_user_stats(user_id, completed_inc, earned_inc):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET completed_jobs = completed_jobs + ?, total_earned = total_earned + ? WHERE id = ?",
                (completed_inc, earned_inc, user_id)
            )
            await db.commit()

    @staticmethod
    async def get_active_jobs(user_id):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM vacancies WHERE assigned_user_id = ? AND status = 'in_progress'", (user_id,))
            return await cursor.fetchall()

    @staticmethod
    async def get_all_vacancies():
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM vacancies ORDER BY created_at DESC")
            return await cursor.fetchall()

    @staticmethod
    async def get_all_users_detailed():
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users")
            return await cursor.fetchall()

    @staticmethod
    async def delete_vacancy(v_id):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE vacancies SET status = 'deleted' WHERE id = ?", (v_id,))
            await db.commit()
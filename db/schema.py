import sqlite3
from pathlib import Path

# SQLite database file — created automatically if it does not exist
DB_PATH = Path("smart_planner.db")


def create_tables():
    """Create all required tables and run safe migrations on every startup."""

    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ── Core tables ───────────────────────────────────────────────────────────

    # Users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    );
    """)

    # User preferences (workout goals, preferred time, buffer, home city)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS preferences (
        user_id INTEGER PRIMARY KEY,
        workouts_per_week INTEGER NOT NULL,
        workout_duration_min INTEGER NOT NULL,
        preferred_time TEXT NOT NULL,
        buffer_min INTEGER NOT NULL DEFAULT 45,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)

    # Shift templates (morning / afternoon / night) — reserved for future use
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shift_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)

    # Weekly shift assignments
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weekly_shifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        week_start_date TEXT NOT NULL,
        day_of_week INTEGER NOT NULL,
        template_id INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(template_id) REFERENCES shift_templates(id)
    );
    """)

    # Recurring weekly study blocks
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS study_blocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        day_of_week INTEGER NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        label TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)

    # Scheduled workouts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        day_of_week INTEGER NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        label TEXT,
        completed INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)

    # Tasks
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        due_date TEXT,
        priority TEXT NOT NULL DEFAULT 'medium',
        status TEXT NOT NULL DEFAULT 'pending',
        estimated_hours REAL NOT NULL DEFAULT 1.0,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)

    # User-accepted task sessions (confirmed time slots for tasks)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        task_id INTEGER NOT NULL,
        day_of_week INTEGER NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(task_id) REFERENCES tasks(id)
    );
    """)

    # ── Migrations (safe to run on every startup) ─────────────────────────────

    # workouts: completed flag
    try:
        cursor.execute("ALTER TABLE workouts ADD COLUMN completed INTEGER NOT NULL DEFAULT 0")
    except Exception:
        pass

    # preferences: home city for weather forecasts
    try:
        cursor.execute("ALTER TABLE preferences ADD COLUMN home_city TEXT DEFAULT ''")
    except Exception:
        pass

    # study_blocks: physical location + commute time
    try:
        cursor.execute("ALTER TABLE study_blocks ADD COLUMN location TEXT DEFAULT ''")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE study_blocks ADD COLUMN commute_min INTEGER DEFAULT 0")
    except Exception:
        pass

    # workouts: physical location + commute time
    try:
        cursor.execute("ALTER TABLE workouts ADD COLUMN location TEXT DEFAULT ''")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE workouts ADD COLUMN commute_min INTEGER DEFAULT 0")
    except Exception:
        pass

    conn.commit()
    conn.close()

    print("✅ Database and tables created successfully!")


if __name__ == "__main__":
    create_tables()

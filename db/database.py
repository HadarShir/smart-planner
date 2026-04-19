import sqlite3
from pathlib import Path

DB_PATH = Path("smart_planner.db")


def get_connection():
    """Return a new SQLite connection to the database."""
    return sqlite3.connect(DB_PATH)


# ── Users ──────────────────────────────────────────────────────────────────────

def create_user(name: str):
    """Insert a new user."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()


def get_all_users():
    """Return a list of (id, name) tuples for all users."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM users")
    users  = cursor.fetchall()
    conn.close()
    return users


# ── Preferences ────────────────────────────────────────────────────────────────

def save_preferences(user_id: int,
                     workouts_per_week: int,
                     workout_duration_min: int,
                     preferred_time: str,
                     buffer_min: int,
                     home_city: str = ""):
    """Insert or replace the user's preferences."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO preferences
    (user_id, workouts_per_week, workout_duration_min, preferred_time, buffer_min, home_city)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, workouts_per_week, workout_duration_min, preferred_time, buffer_min, home_city))
    conn.commit()
    conn.close()


def get_preferences(user_id: int):
    """Return (workouts_per_week, workout_duration_min, preferred_time, buffer_min, home_city)."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT workouts_per_week, workout_duration_min, preferred_time, buffer_min,
           COALESCE(home_city, '') as home_city
    FROM preferences
    WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row


# ── Study Blocks ───────────────────────────────────────────────────────────────

def add_study_block(user_id: int, day_of_week: int, start_time: str, end_time: str,
                    label: str, location: str = "", commute_min: int = 0):
    """Insert a new recurring study block."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO study_blocks (user_id, day_of_week, start_time, end_time, label, location, commute_min)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, day_of_week, start_time, end_time, label, location, commute_min))
    conn.commit()
    conn.close()


def get_study_blocks(user_id: int):
    """Return (id, day_of_week, start_time, end_time, label, location, commute_min)."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, day_of_week, start_time, end_time, label,
           COALESCE(location, '') as location,
           COALESCE(commute_min, 0) as commute_min
    FROM study_blocks
    WHERE user_id = ?
    ORDER BY day_of_week, start_time
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def update_study_block(block_id: int, day_of_week: int, start_time: str, end_time: str,
                       label: str, location: str = "", commute_min: int = 0):
    """Update all fields of an existing study block."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE study_blocks
    SET day_of_week = ?, start_time = ?, end_time = ?, label = ?, location = ?, commute_min = ?
    WHERE id = ?
    """, (day_of_week, start_time, end_time, label, location, commute_min, block_id))
    conn.commit()
    conn.close()


def delete_study_block(block_id: int):
    """Delete a study block by id."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM study_blocks WHERE id = ?", (block_id,))
    conn.commit()
    conn.close()


# ── Workouts ───────────────────────────────────────────────────────────────────

def add_workout(user_id: int, day_of_week: int, start_time: str, end_time: str,
                label: str, location: str = "", commute_min: int = 0):
    """Insert a new scheduled workout."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO workouts (user_id, day_of_week, start_time, end_time, label, location, commute_min)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, day_of_week, start_time, end_time, label, location, commute_min))
    conn.commit()
    conn.close()


def get_workouts(user_id: int):
    """Return (id, day_of_week, start_time, end_time, label, completed, location, commute_min)."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, day_of_week, start_time, end_time, label, completed,
           COALESCE(location, '') as location,
           COALESCE(commute_min, 0) as commute_min
    FROM workouts
    WHERE user_id = ?
    ORDER BY day_of_week, start_time
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def update_workout(workout_id: int, day_of_week: int, start_time: str, end_time: str,
                   label: str, location: str = "", commute_min: int = 0):
    """Update day, time, label, location and commute of an existing workout."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE workouts
    SET day_of_week = ?, start_time = ?, end_time = ?, label = ?, location = ?, commute_min = ?
    WHERE id = ?
    """, (day_of_week, start_time, end_time, label, location, commute_min, workout_id))
    conn.commit()
    conn.close()


def delete_workout(workout_id: int):
    """Delete a workout by id."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))
    conn.commit()
    conn.close()


def mark_workout_completed(workout_id: int, completed: bool):
    """Toggle a workout's completed status."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE workouts SET completed = ? WHERE id = ?",
        (1 if completed else 0, workout_id)
    )
    conn.commit()
    conn.close()


# ── Tasks ──────────────────────────────────────────────────────────────────────

def add_task(user_id: int, title: str, description: str,
             due_date: str, priority: str, estimated_hours: float):
    """Insert a new task and return its new id."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO tasks (user_id, title, description, due_date, priority, status, estimated_hours)
    VALUES (?, ?, ?, ?, ?, 'pending', ?)
    """, (user_id, title, description, due_date, priority, estimated_hours))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id


def get_tasks(user_id: int, status_filter: str = None):
    """
    Return tasks for a user, ordered by priority then due date.
    status_filter: 'pending' | 'done' | None (all)
    """
    conn   = get_connection()
    cursor = conn.cursor()
    if status_filter:
        cursor.execute("""
        SELECT id, title, description, due_date, priority, status, estimated_hours
        FROM tasks
        WHERE user_id = ? AND status = ?
        ORDER BY
            CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
            due_date ASC
        """, (user_id, status_filter))
    else:
        cursor.execute("""
        SELECT id, title, description, due_date, priority, status, estimated_hours
        FROM tasks
        WHERE user_id = ?
        ORDER BY
            CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
            due_date ASC
        """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    cols = ["id", "title", "description", "due_date", "priority", "status", "estimated_hours"]
    return [dict(zip(cols, r)) for r in rows]


def update_task_status(task_id: int, status: str):
    """Mark a task as 'pending' or 'done'."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
    conn.commit()
    conn.close()


def update_task(task_id: int, title: str, description: str,
                due_date: str, priority: str, estimated_hours: float):
    """Edit all fields of an existing task."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE tasks
    SET title = ?, description = ?, due_date = ?, priority = ?, estimated_hours = ?
    WHERE id = ?
    """, (title, description, due_date, priority, estimated_hours, task_id))
    conn.commit()
    conn.close()


def delete_task(task_id: int):
    """Delete a task by id."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


# ── Task Sessions ──────────────────────────────────────────────────────────────

def add_task_session(user_id: int, task_id: int, day_of_week: int,
                     start_time: str, end_time: str):
    """Insert a user-accepted task session into the schedule."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO task_sessions (user_id, task_id, day_of_week, start_time, end_time)
    VALUES (?, ?, ?, ?, ?)
    """, (user_id, task_id, day_of_week, start_time, end_time))
    conn.commit()
    conn.close()


def get_task_sessions(user_id: int):
    """Return all accepted task sessions for a user as a list of dicts."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT ts.id, ts.task_id, t.title, t.priority, ts.day_of_week, ts.start_time, ts.end_time
    FROM task_sessions ts
    JOIN tasks t ON ts.task_id = t.id
    WHERE ts.user_id = ?
    ORDER BY ts.day_of_week, ts.start_time
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    cols = ["id", "task_id", "title", "priority", "day_of_week", "start_time", "end_time"]
    return [dict(zip(cols, r)) for r in rows]


def delete_task_session(session_id: int):
    """Remove a single task session by id."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM task_sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

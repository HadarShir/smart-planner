"""
One-time script: adds location + commute_min to all existing study blocks and workouts.
Run once from the pythonProject11 folder:  python update_locations.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("smart_planner.db")

conn   = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ── Study blocks → Ben Gurion University, 7 min walk ──────────────────────────
cursor.execute("""
    UPDATE study_blocks
    SET location = 'Ben Gurion University', commute_min = 7
    WHERE (location IS NULL OR location = '')
""")
sb_updated = cursor.rowcount
print(f"✅ Updated {sb_updated} study block(s) → Ben Gurion University, 7 min")

# ── Workouts → Gym by the sea (גב ים), 25 min walk ────────────────────────────
cursor.execute("""
    UPDATE workouts
    SET location = 'גב ים', commute_min = 25
    WHERE (location IS NULL OR location = '')
""")
wo_updated = cursor.rowcount
print(f"✅ Updated {wo_updated} workout(s) → גב ים, 25 min")

conn.commit()
conn.close()
print("\nDone! Restart the app to see the changes.")

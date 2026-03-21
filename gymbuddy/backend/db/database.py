import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "gymbuddy.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY,
            fitness_level TEXT DEFAULT 'beginner',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES user_profile(id) ON DELETE CASCADE,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            duration_mins INTEGER,
            equipment TEXT,
            energy_level TEXT
        );

        CREATE TABLE IF NOT EXISTS session_exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES user_profile(id) ON DELETE CASCADE,
            exercise_name TEXT,
            muscle_group TEXT,
            sets INTEGER,
            reps TEXT,
            notes TEXT
        );
    """)

    # Insert default user profile if not exists
    cursor.execute("INSERT OR IGNORE INTO user_profile (id) VALUES (1)")

    conn.commit()
    conn.close()

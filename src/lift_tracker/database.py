import os
import sqlite3
from datetime import datetime, timezone


def get_connection() -> sqlite3.Connection:
    """Open and return a SQLite connection using DB_PATH from the environment."""
    db_path = os.getenv("DB_PATH", "lift_tracker.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create all tables if they don't exist. Called once at app startup."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS programs (
                id          INTEGER PRIMARY KEY,
                name        TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id          INTEGER PRIMARY KEY,
                program_id  INTEGER REFERENCES programs(id),
                date        TEXT NOT NULL,
                notes       TEXT,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sets (
                id           INTEGER PRIMARY KEY,
                session_id   INTEGER NOT NULL REFERENCES sessions(id),
                exercise     TEXT NOT NULL,
                muscle_group TEXT,
                weight       REAL NOT NULL,
                reps         INTEGER NOT NULL,
                set_number   INTEGER NOT NULL,
                created_at   TEXT NOT NULL
            );
        """)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


# --- Programs ---

class DuplicateError(Exception):
    pass


def create_program(name: str, description: str | None) -> dict:
    """Insert a new program. Raises DuplicateError if the name already exists."""
    with get_connection() as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO programs (name, description, created_at) VALUES (?, ?, ?)",
                (name, description, _now()),
            )
        except sqlite3.IntegrityError:
            raise DuplicateError(f"Program '{name}' already exists")
        row = conn.execute(
            "SELECT * FROM programs WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return _row_to_dict(row)


def list_programs() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM programs ORDER BY created_at DESC").fetchall()
        return [_row_to_dict(r) for r in rows]


def get_program(program_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM programs WHERE id = ?", (program_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None


# --- Sessions ---

def create_session(program_id: int | None, date: str, notes: str | None) -> dict:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO sessions (program_id, date, notes, created_at) VALUES (?, ?, ?, ?)",
            (program_id, date, notes, _now()),
        )
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return _row_to_dict(row)


def get_session_with_sets(session_id: int) -> dict | None:
    """Return a session with its sets nested under a 'sets' key, or None if not found."""
    with get_connection() as conn:
        session_row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not session_row:
            return None
        session = _row_to_dict(session_row)
        set_rows = conn.execute(
            "SELECT * FROM sets WHERE session_id = ? ORDER BY set_number",
            (session_id,),
        ).fetchall()
        session["sets"] = [_row_to_dict(r) for r in set_rows]
        return session


# --- Sets ---

def add_set(
    session_id: int,
    exercise: str,
    muscle_group: str | None,
    weight: float,
    reps: int,
    set_number: int,
) -> dict:
    """Insert a set. Exercise name is normalized to lowercase on write."""
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO sets
               (session_id, exercise, muscle_group, weight, reps, set_number, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, exercise.lower(), muscle_group, weight, reps, set_number, _now()),
        )
        row = conn.execute(
            "SELECT * FROM sets WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return _row_to_dict(row)


# --- Exercise queries ---

def get_exercise_history(exercise: str) -> list[dict]:
    """Return all sets for an exercise across all sessions, ordered by date. Includes session_date."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT s.*, se.date as session_date
               FROM sets s
               JOIN sessions se ON se.id = s.session_id
               WHERE s.exercise = ?
               ORDER BY se.date ASC, s.set_number ASC""",
            (exercise.lower(),),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def get_program_sessions(program_id: int) -> list[dict]:
    """Return all sessions for a program, each with sets nested under a 'sets' key."""
    with get_connection() as conn:
        session_rows = conn.execute(
            "SELECT * FROM sessions WHERE program_id = ? ORDER BY date ASC",
            (program_id,),
        ).fetchall()
        sessions = []
        for sr in session_rows:
            session = _row_to_dict(sr)
            set_rows = conn.execute(
                "SELECT * FROM sets WHERE session_id = ? ORDER BY set_number",
                (session["id"],),
            ).fetchall()
            session["sets"] = [_row_to_dict(r) for r in set_rows]
            sessions.append(session)
        return sessions

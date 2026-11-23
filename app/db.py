"""SQLite adatréteg. Az adatbázis fájlja a DB_PATH környezeti változóból jön."""
import os
import sqlite3
import threading

_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(os.getenv("DB_PATH", "fitbook.db"), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                trainer TEXT NOT NULL,
                starts_at TEXT NOT NULL,
                capacity INTEGER NOT NULL CHECK (capacity > 0)
            );
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                member TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('ACTIVE','WAITLISTED','CANCELLED')),
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f','now'))
            );
            """
        )


def _session_row(conn: sqlite3.Connection, session_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT s.*,
               (SELECT COUNT(*) FROM bookings b WHERE b.session_id = s.id AND b.status = 'ACTIVE') AS booked,
               (SELECT COUNT(*) FROM bookings b WHERE b.session_id = s.id AND b.status = 'WAITLISTED') AS waitlisted
        FROM sessions s WHERE s.id = ?
        """,
        (session_id,),
    ).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["free_places"] = data["capacity"] - data["booked"]
    return data


def list_sessions() -> list[dict]:
    with _connect() as conn:
        ids = [r["id"] for r in conn.execute("SELECT id FROM sessions ORDER BY starts_at")]
        return [_session_row(conn, i) for i in ids]


def create_session(name: str, trainer: str, starts_at: str, capacity: int) -> dict:
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO sessions (name, trainer, starts_at, capacity) VALUES (?, ?, ?, ?)",
            (name, trainer, starts_at, capacity),
        )
        return _session_row(conn, cur.lastrowid)


def get_session(session_id: int) -> dict | None:
    with _connect() as conn:
        return _session_row(conn, session_id)


def has_open_booking(session_id: int, member: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM bookings WHERE session_id = ? AND member = ? AND status != 'CANCELLED'",
            (session_id, member),
        ).fetchone()
        return row is not None


def create_booking(session_id: int, member: str, status: str) -> dict:
    with _lock, _connect() as conn:
        # A zár alatt újraszámoljuk a szabad helyet, így párhuzamos kéréseknél sincs túlfoglalás.
        session = _session_row(conn, session_id)
        if status == "ACTIVE" and session["free_places"] <= 0:
            status = "WAITLISTED"
        cur = conn.execute(
            "INSERT INTO bookings (session_id, member, status) VALUES (?, ?, ?)",
            (session_id, member, status),
        )
        return dict(conn.execute("SELECT * FROM bookings WHERE id = ?", (cur.lastrowid,)).fetchone())


def get_booking(booking_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        return dict(row) if row else None


def cancel_booking(booking_id: int) -> int | None:
    """Lemondja a foglalást; ha aktív volt, előlépteti az első várólistást. Visszaadja az előléptetett foglalás id-ját."""
    with _lock, _connect() as conn:
        booking = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        conn.execute("UPDATE bookings SET status = 'CANCELLED' WHERE id = ?", (booking_id,))
        if booking["status"] != "ACTIVE":
            return None
        nxt = conn.execute(
            "SELECT id FROM bookings WHERE session_id = ? AND status = 'WAITLISTED' ORDER BY created_at, id LIMIT 1",
            (booking["session_id"],),
        ).fetchone()
        if nxt is None:
            return None
        conn.execute("UPDATE bookings SET status = 'ACTIVE' WHERE id = ?", (nxt["id"],))
        return nxt["id"]

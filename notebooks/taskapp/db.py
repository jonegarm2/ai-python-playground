"""
db.py — SQLite database layer for Weekly Task Manager
"""
import sqlite3
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "tasks.db"

LISTS = ("work", "house")
DEFAULT_LIST = "work"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def current_week_str() -> str:
    """ISO week string like '2025-W03' for rollover tracking."""
    today = date.today()
    return f"{today.isocalendar()[0]}-W{today.isocalendar()[1]:02d}"


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                list        TEXT NOT NULL DEFAULT 'work'
                                CHECK(list IN ('work', 'house')),
                priority    TEXT NOT NULL DEFAULT 'medium'
                                CHECK(priority IN ('low','medium','high')),
                status      TEXT NOT NULL DEFAULT 'pending'
                                CHECK(status IN ('pending','done')),
                week_added  TEXT NOT NULL,
                created     TEXT NOT NULL,
                updated     TEXT NOT NULL
            );
        """)
        # migrate old schema if upgrading from v1
        cols = [r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()]
        if "project_id" in cols and "list" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN list TEXT NOT NULL DEFAULT 'work'")
            conn.execute("ALTER TABLE tasks ADD COLUMN week_added TEXT NOT NULL DEFAULT ''")


# ── Tasks CRUD ────────────────────────────────────────────────────────────────

def add_task(title: str, list_name: str = DEFAULT_LIST, priority: str = "medium") -> dict:
    list_name = _validate_list(list_name)
    now = datetime.utcnow().isoformat()
    week = current_week_str()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tasks(title,list,priority,status,week_added,created,updated) VALUES(?,?,?,?,?,?,?)",
            (title, list_name, priority, "pending", week, now, now),
        )
        return get_task(cur.lastrowid)


def get_task(task_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return _enrich(dict(row)) if row else None


def list_tasks(status: str = "pending", list_name: str = None) -> list[dict]:
    with get_conn() as conn:
        if list_name:
            list_name = _validate_list(list_name)
            rows = conn.execute("""
                SELECT * FROM tasks WHERE status=? AND list=?
                ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, id
            """, (status, list_name)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM tasks WHERE status=?
                ORDER BY list, CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, id
            """, (status,)).fetchall()
        return [_enrich(dict(r)) for r in rows]


def update_task(task_id: int, **fields) -> dict | None:
    allowed = {"title", "priority", "status", "list"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if "list" in updates:
        updates["list"] = _validate_list(updates["list"])
    if not updates:
        return get_task(task_id)
    updates["updated"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [task_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE tasks SET {set_clause} WHERE id=?", values)
    return get_task(task_id)


def delete_task(task_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        return cur.rowcount > 0


def mark_done(task_id: int) -> dict | None:
    return update_task(task_id, status="done")


def set_priority(task_id: int, priority: str) -> dict | None:
    priority = priority.lower()
    if priority not in ("low", "medium", "high"):
        raise ValueError(f"Invalid priority: {priority}")
    return update_task(task_id, priority=priority)


# ── Rollover helpers ──────────────────────────────────────────────────────────

def weeks_pending(task: dict) -> int:
    """How many weeks ago was this task added? 0 = this week, 1 = last week, etc."""
    current = current_week_str()
    if not task.get("week_added") or task["week_added"] == current:
        return 0
    try:
        cy, cw = _parse_week(current)
        ty, tw = _parse_week(task["week_added"])
        return max(0, (cy * 52 + cw) - (ty * 52 + tw))
    except Exception:
        return 0


# ── Private helpers ───────────────────────────────────────────────────────────

def _validate_list(name: str) -> str:
    name = name.strip().lower()
    if name in ("house", "home", "h", "personal"):
        return "house"
    if name in ("work", "w", "job", "office"):
        return "work"
    raise ValueError(f"List must be 'work' or 'house', got: '{name}'")


def _parse_week(week_str: str):
    year, w = week_str.split("-W")
    return int(year), int(w)


def _enrich(task: dict) -> dict:
    task["weeks_pending"] = weeks_pending(task)
    return task

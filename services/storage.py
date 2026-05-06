import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

from models.task import Task

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = DATA_DIR / "exports"
DB_PATH = DATA_DIR / "tasks.db"
SETTINGS_PATH = DATA_DIR / "settings.json"


class Storage:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                due_at TEXT,
                tags TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'pending',
                completed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def add_task(self, title: str, due_at: datetime | None, tags: list[str]) -> Task:
        now = datetime.now().isoformat(timespec="seconds")
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO tasks (title, due_at, tags, status, created_at, updated_at)
            VALUES (?, ?, ?, 'pending', ?, ?)
            """,
            (title.strip(), self._dump_dt(due_at), json.dumps(tags, ensure_ascii=False), now, now),
        )
        self.conn.commit()
        return self.get_task(cursor.lastrowid)

    def update_task(self, task_id: int, title: str, due_at: datetime | None, tags: list[str]) -> Task:
        updated_at = datetime.now().isoformat(timespec="seconds")
        self.conn.execute(
            """
            UPDATE tasks
            SET title = ?, due_at = ?, tags = ?, updated_at = ?
            WHERE id = ?
            """,
            (title.strip(), self._dump_dt(due_at), json.dumps(tags, ensure_ascii=False), updated_at, task_id),
        )
        self.conn.commit()
        return self.get_task(task_id)

    def complete_task(self, task_id: int) -> Task:
        timestamp = datetime.now().isoformat(timespec="seconds")
        self.conn.execute(
            """
            UPDATE tasks
            SET status = 'completed', completed_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (timestamp, timestamp, task_id),
        )
        self.conn.commit()
        return self.get_task(task_id)

    def delete_task(self, task_id: int):
        self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()

    def get_task(self, task_id: int) -> Task:
        row = self.conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise ValueError(f"Task {task_id} not found")
        return self._row_to_task(row)

    def list_tasks(self, status: str | None = None, tag: str | None = None) -> list[Task]:
        rows = self.conn.execute(
            "SELECT * FROM tasks ORDER BY CASE WHEN due_at IS NULL THEN 1 ELSE 0 END, due_at ASC, created_at DESC"
        ).fetchall()
        tasks = [self._row_to_task(row) for row in rows]
        if status in {"pending", "completed"}:
            tasks = [task for task in tasks if task.status == status]
        if tag:
            tasks = [task for task in tasks if tag in task.tags]
        return tasks

    def pending_titles(self) -> list[str]:
        return [task.title for task in self.list_tasks(status="pending")]

    def completed_tasks_for_date(self, target_day: date) -> list[Task]:
        tasks = self.list_tasks(status="completed")
        return [
            task for task in tasks if task.completed_at is not None and task.completed_at.date() == target_day
        ]

    def load_settings(self) -> dict:
        default_settings = {
            "corner": "bottom-right",
            "opacity": 0.72,
            "interval_seconds": 10,
            "click_through": False,
            "always_on_top": True,
            "paused": False,
            "position": None,
            "last_exported_date": None,
        }
        if not SETTINGS_PATH.exists():
            return default_settings
        try:
            raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default_settings
        default_settings.update(raw)
        return default_settings

    def save_settings(self, settings: dict):
        SETTINGS_PATH.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")

    def update_settings(self, updates: dict) -> dict:
        settings = self.load_settings()
        settings.update(updates)
        self.save_settings(settings)
        return settings

    @staticmethod
    def _dump_dt(value: datetime | None) -> str | None:
        return value.isoformat(timespec="seconds") if value else None

    @staticmethod
    def _parse_dt(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value)

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            due_at=self._parse_dt(row["due_at"]),
            tags=json.loads(row["tags"] or "[]"),
            status=row["status"],
            completed_at=self._parse_dt(row["completed_at"]),
            created_at=self._parse_dt(row["created_at"]),
            updated_at=self._parse_dt(row["updated_at"]),
        )

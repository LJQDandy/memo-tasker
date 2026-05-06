from datetime import datetime, time, timedelta

from PySide6.QtCore import QObject, QTimer, Signal

# 提前多少分钟提醒（即将到期）
_WARN_MINUTES = 30


class DailyExportScheduler(QObject):
    export_finished = Signal(str)
    # (task_id, title, due_at_str, kind)  kind: 'soon' | 'overdue'
    task_due_reminder = Signal(int, str, str, str)

    def __init__(self, storage, exporter):
        super().__init__()
        self.storage = storage
        self.exporter = exporter
        self._notified_ids: set[int] = set()
        self.timer = QTimer(self)
        self.timer.setInterval(60000)          # 每分钟检查一次
        self.timer.timeout.connect(self.check)

    def start(self):
        self.timer.start()
        self.check()

    def check(self):
        self._check_export()
        self._check_due_reminders()

    def _check_export(self):
        now = datetime.now()
        if now.time() < time(17, 55):
            return
        settings = self.storage.load_settings()
        today = now.date().isoformat()
        if settings.get("last_exported_date") != today:
            self.export_today(force=True)

    def _check_due_reminders(self):
        now = datetime.now()
        warn_threshold = now + timedelta(minutes=_WARN_MINUTES)
        for task in self.storage.list_tasks(status="pending"):
            if task.id in self._notified_ids or task.due_at is None:
                continue
            due = task.due_at
            if due <= now:
                kind = "overdue"
            elif due <= warn_threshold:
                kind = "soon"
            else:
                continue
            self._notified_ids.add(task.id)
            due_str = due.strftime("%H:%M")
            self.task_due_reminder.emit(task.id, task.title, due_str, kind)

    def reset_notified(self, task_id: int):
        """当任务被完成或删除时，从已提醒集合中移除，避免状态泄漏。"""
        self._notified_ids.discard(task_id)

    def export_today(self, force: bool = False):
        now = datetime.now()
        if not force and now.time() < time(17, 55):
            return None
        path = self.exporter.export_for_day(now.date())
        self.storage.update_settings({"last_exported_date": now.date().isoformat()})
        self.export_finished.emit(str(path))
        return path
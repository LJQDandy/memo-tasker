from collections import Counter
from datetime import date, datetime
from pathlib import Path

from services.storage import EXPORTS_DIR, Storage


class DailyExporter:
    def __init__(self, storage: Storage):
        self.storage = storage

    def export_for_day(self, target_day: date | None = None) -> Path:
        target_day = target_day or date.today()
        tasks = self.storage.completed_tasks_for_date(target_day)
        path = EXPORTS_DIR / f"{target_day.isoformat()}-done.md"
        lines = [
            f"# {target_day.isoformat()} 今日已完成任务",
            "",
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 已完成列表",
            "",
        ]
        if tasks:
            for task in tasks:
                completed_at = task.completed_at.strftime("%H:%M") if task.completed_at else "--:--"
                tags = " ".join(task.tags)
                suffix = f" {tags}" if tags else ""
                lines.append(f"- [{completed_at}] {task.title}{suffix}")
        else:
            lines.append("- 今天还没有完成的任务")

        tag_counter = Counter(tag for task in tasks for tag in task.tags)
        lines.extend([
            "",
            "## 统计",
            "",
            f"- 完成任务数：{len(tasks)}",
        ])
        if tag_counter:
            distribution = "，".join(f"{tag} {count}" for tag, count in sorted(tag_counter.items()))
            lines.append(f"- 标签分布：{distribution}")
        else:
            lines.append("- 标签分布：无")

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path
# Memo Tasker

A local Windows desktop task recorder with a floating overlay window that keeps your most urgent tasks always in sight.

一个面向 Windows 的本地任务记录工具，角落悬浮窗让最紧急的任务始终可见。

![Memo Tasker screenshot](assets/screenshot.png)

---

## Features

- **Two-panel layout** — left side for task list, right side for quick entry and overlay settings
- **Task fields** — title, due date/time, and `#tags`
- **Auto-sorted** — pending tasks sorted by due time, earliest first
- **Floating overlay** — semi-transparent, always-on-top window that cycles through pending task titles in a corner of your screen
  - Draggable, resizable opacity, click-through mode, pause/resume
  - Right-click context menu for quick controls
- **System tray** — minimize to tray, restore from tray, show/hide overlay
- **Due reminders** — tray bubble notification 30 minutes before a task is due, and again when overdue
- **Daily export** — auto-generates a Markdown file of completed tasks at 17:55 every day; missed exports are backfilled on next launch
- **Local storage** — SQLite database, no cloud dependency

---

## 功能

- **双栏布局** — 左侧任务列表，右侧快速录入与悬浮窗设置
- **任务字段** — 标题、截止时间、`#标签`
- **自动排序** — 未完成任务按截止时间升序排列
- **悬浮窗** — 半透明置顶窗口，在屏幕角落轮播未完成任务标题
  - 可拖动、透明度调节、点击穿透、暂停/恢复轮播
  - 右键菜单快捷控制
- **系统托盘** — 最小化到托盘，托盘菜单可恢复主界面/悬浮窗
- **到期提醒** — 任务到期前 30 分钟及超时后均有托盘气泡提醒
- **每日导出** — 每天 17:55 自动生成当日完成任务 Markdown；程序未开启时错过的导出会在下次启动时补生成
- **本地存储** — SQLite 数据库，无云端依赖

---

## Requirements

- Windows 10 / 11
- Python 3.10+
- PySide6

## Getting Started

```powershell
pip install -r requirements.txt
python main.py
```

Or double-click **启动 Memo Tasker.bat** to launch without a terminal window.

---

## Data Files

All data is stored locally in the project folder:

```
data/
  tasks.db          # SQLite task database
  settings.json     # overlay window preferences
  exports/
    YYYY-MM-DD-done.md   # daily completed task log
```

> `data/` is excluded from version control via `.gitignore`.

---

## License

[MIT](LICENSE) © 2026 LJQDandy
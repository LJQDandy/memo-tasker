from PySide6.QtWidgets import QApplication
import sys

from services.exporter import DailyExporter
from services.scheduler import DailyExportScheduler
from services.storage import Storage
from ui.main_window import MainWindow
from ui.overlay_window import OverlayWindow
from ui.tray import AppTray

if __name__ == "__main__":
    app = QApplication(sys.argv)
    storage = Storage()
    exporter = DailyExporter(storage)
    scheduler = DailyExportScheduler(storage, exporter)
    main_window = MainWindow(storage, scheduler.export_today)
    overlay = OverlayWindow(storage)
    tray = AppTray(app, main_window, overlay)
    main_window.set_tray_controller(tray)

    main_window.tasks_changed.connect(overlay.refresh_tasks)
    main_window.settings_changed.connect(overlay.apply_settings)
    overlay.settings_changed.connect(main_window.apply_settings_to_controls)
    overlay.settings_changed.connect(overlay.apply_settings)
    overlay.request_show_main.connect(main_window.showNormal)
    overlay.request_show_main.connect(main_window.raise_)

    # 托盘气泡通知
    scheduler.task_due_reminder.connect(tray.notify_task_due)
    scheduler.export_finished.connect(tray.notify_export_done)
    # 任务完成或删除时重置已提醒状态，避免下次重新打开程序后不再提醒
    main_window.task_completed.connect(scheduler.reset_notified)
    main_window.task_deleted.connect(scheduler.reset_notified)

    main_window.show()
    overlay.show()
    tray.show()
    scheduler.start()
    sys.exit(app.exec())

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QStyle, QSystemTrayIcon


class AppTray(QObject):
    def __init__(self, app, main_window, overlay_window):
        super().__init__()
        self.app = app
        self.main_window = main_window
        self.overlay_window = overlay_window
        icon = app.style().standardIcon(QStyle.SP_FileDialogDetailedView)
        self.tray_icon = QSystemTrayIcon(icon, app)
        self.tray_icon.setToolTip("Memo Tasker")
        self.tray_icon.activated.connect(self._handle_activation)
        self._build_menu(icon)

    def _build_menu(self, icon: QIcon):
        menu = QMenu()
        menu.setLayoutDirection(Qt.LeftToRight)

        show_action = QAction(icon, "打开主界面", menu)
        show_action.triggered.connect(self.show_main_window)

        toggle_overlay_action = QAction("显示或隐藏悬浮窗", menu)
        toggle_overlay_action.triggered.connect(self.toggle_overlay)

        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(self.quit_application)

        menu.addAction(show_action)
        menu.addAction(toggle_overlay_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray_icon.setContextMenu(menu)

    def show(self):
        self.tray_icon.show()

    def notify_minimized(self):
        self.tray_icon.showMessage(
            "Memo Tasker",
            "主窗口已最小化到系统托盘，可从托盘菜单重新打开。",
            QSystemTrayIcon.Information,
            2500,
        )

    def notify_task_due(self, task_id: int, title: str, due_str: str, kind: str):
        if kind == "overdue":
            headline = "任务已超时"
            body = f"「{title}」到期时间 {due_str}，请尽快处理。"
            icon = QSystemTrayIcon.Warning
        else:
            headline = "任务即将到期"
            body = f"「{title}」将在 {due_str} 到期（30 分钟内）。"
            icon = QSystemTrayIcon.Information
        self.tray_icon.showMessage(headline, body, icon, 6000)

    def notify_export_done(self, path: str):
        import pathlib
        filename = pathlib.Path(path).name
        self.tray_icon.showMessage(
            "Memo Tasker · 已导出",
            f"今日完成任务已保存到\n{filename}",
            QSystemTrayIcon.Information,
            4000,
        )

    def show_main_window(self):
        self.main_window.showNormal()
        self.main_window.raise_()
        self.main_window.activateWindow()
        if not self.overlay_window.isVisible():
            self.overlay_window.show()

    def toggle_overlay(self):
        if self.overlay_window.isVisible():
            self.overlay_window.hide()
        else:
            self.overlay_window.show()

    def quit_application(self):
        self.main_window.allow_exit()
        self.overlay_window.close()
        self.tray_icon.hide()
        self.app.quit()

    def _handle_activation(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show_main_window()
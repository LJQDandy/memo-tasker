import ctypes

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QCursor
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QLabel, QMenu, QVBoxLayout, QWidget


class OverlayWindow(QWidget):
    settings_changed = Signal(dict)
    request_show_main = Signal()

    def __init__(self, storage):
        super().__init__()
        self.storage = storage
        self.settings = self.storage.load_settings()
        self.drag_offset = QPoint()
        self.tasks = []
        self.current_index = 0

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(360, 84)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)

        self.card = QFrame(self)
        self.card.setObjectName("overlayCard")
        card_shadow = QGraphicsDropShadowEffect(self)
        card_shadow.setBlurRadius(28)
        card_shadow.setOffset(0, 10)
        card_shadow.setColor(QColor(10, 17, 28, 55))
        self.card.setGraphicsEffect(card_shadow)
        root_layout.addWidget(self.card)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(22, 14, 22, 14)
        card_layout.setSpacing(0)

        self.label = QLabel(self.card)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(False)
        self.label.setObjectName("overlayTitle")
        self.card.setStyleSheet(
            """
            QFrame#overlayCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(23, 33, 48, 220),
                    stop:0.45 rgba(28, 49, 63, 216),
                    stop:1 rgba(57, 76, 66, 212));
                border: 1px solid rgba(255, 255, 255, 55);
                border-radius: 20px;
            }
            QLabel#overlayTitle {
                color: rgba(250, 247, 241, 245);
                font-family: "Microsoft YaHei UI";
                font-size: 18px;
                font-weight: 700;
                padding: 10px 4px;
            }
            """
        )
        card_layout.addWidget(self.label)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_task)
        self.apply_settings(self.settings)
        self.refresh_tasks()

    def refresh_tasks(self):
        self.tasks = [task.title for task in self.storage.list_tasks(status="pending")]
        self.current_index = 0
        self._render_current()

    def apply_settings(self, settings: dict):
        self.settings = settings
        self.setWindowOpacity(settings["opacity"])
        self.timer.setInterval(settings["interval_seconds"] * 1000)
        if settings["paused"]:
            self.timer.stop()
        else:
            self.timer.start()
        self._apply_window_flags(settings["always_on_top"])
        self._apply_position(settings)
        self._apply_click_through(settings["click_through"])
        self._render_current()

    def next_task(self):
        if not self.tasks:
            self.label.setText("暂无待办任务")
            return
        self.current_index = (self.current_index + 1) % len(self.tasks)
        self._render_current()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        pause_text = "继续轮播" if self.settings["paused"] else "暂停轮播"
        click_text = "关闭点击穿透" if self.settings["click_through"] else "开启点击穿透"

        pause_action = QAction(pause_text, self)
        pause_action.triggered.connect(self._toggle_paused)
        click_action = QAction(click_text, self)
        click_action.triggered.connect(self._toggle_click_through)
        open_main_action = QAction("打开主界面", self)
        open_main_action.triggered.connect(self.request_show_main.emit)
        opacity_up_action = QAction("提高透明度", self)
        opacity_up_action.triggered.connect(lambda: self._adjust_opacity(0.05))
        opacity_down_action = QAction("降低透明度", self)
        opacity_down_action.triggered.connect(lambda: self._adjust_opacity(-0.05))

        menu.addAction(open_main_action)
        menu.addAction(pause_action)
        menu.addAction(click_action)
        menu.addAction(opacity_up_action)
        menu.addAction(opacity_down_action)
        menu.exec(QCursor.pos())
        event.accept()

    def mousePressEvent(self, event):
        if self.settings["click_through"]:
            return
        if event.button() == Qt.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.settings["click_through"]:
            return
        if event.buttons() & Qt.LeftButton:
            new_pos = event.globalPosition().toPoint() - self.drag_offset
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if self.settings["click_through"]:
            return
        if event.button() == Qt.LeftButton:
            settings = self.storage.update_settings({"position": [self.x(), self.y()]})
            self.settings_changed.emit(settings)
            event.accept()

    def _render_current(self):
        if not self.tasks:
            self.label.setText("暂无待办任务")
            return
        metrics = self.label.fontMetrics()
        title = self.tasks[self.current_index]
        self.label.setText(metrics.elidedText(title, Qt.ElideRight, self.card.width() - 52))

    def _apply_window_flags(self, always_on_top: bool):
        flags = Qt.FramelessWindowHint | Qt.Tool
        if always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def _apply_position(self, settings: dict):
        if settings.get("position"):
            self.move(*settings["position"])
            return

        geometry = self.screen().availableGeometry() if self.screen() else self.geometry()
        margin = 24
        width = self.width()
        height = self.height()
        positions = {
            "top-left": (geometry.left() + margin, geometry.top() + margin),
            "top-right": (geometry.right() - width - margin, geometry.top() + margin),
            "bottom-left": (geometry.left() + margin, geometry.bottom() - height - margin),
            "bottom-right": (geometry.right() - width - margin, geometry.bottom() - height - margin),
        }
        self.move(*positions.get(settings["corner"], positions["bottom-right"]))

    def _apply_click_through(self, enabled: bool):
        if ctypes.sizeof(ctypes.c_void_p) == 0:
            return
        hwnd = int(self.winId())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        layered = 0x80000
        transparent = 0x20
        if enabled:
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | layered | transparent)
        else:
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, (style | layered) & ~transparent)

    def _toggle_paused(self):
        settings = self.storage.update_settings({"paused": not self.settings["paused"]})
        self.settings_changed.emit(settings)

    def _toggle_click_through(self):
        settings = self.storage.update_settings({"click_through": not self.settings["click_through"]})
        self.settings_changed.emit(settings)

    def _adjust_opacity(self, delta: float):
        opacity = min(0.95, max(0.35, round(self.settings["opacity"] + delta, 2)))
        settings = self.storage.update_settings({"opacity": opacity})
        self.settings_changed.emit(settings)

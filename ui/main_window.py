from datetime import datetime

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.storage import Storage


class MainWindow(QMainWindow):
    tasks_changed = Signal()
    settings_changed = Signal(dict)
    task_completed = Signal(int)   # task_id
    task_deleted = Signal(int)     # task_id

    def __init__(self, storage: Storage, export_today_callback):
        super().__init__()
        self.storage = storage
        self.export_today_callback = export_today_callback
        self.editing_task_id = None
        self._allow_close = False
        self._tray_notified = False
        self.setWindowTitle("工作任务记录器")
        self.resize(1180, 760)
        self._build_ui()
        self._apply_styles()
        self._load_settings_into_controls()
        self.refresh_tasks()

    def set_tray_controller(self, tray_controller):
        self.tray_controller = tray_controller

    def allow_exit(self):
        self._allow_close = True

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            event.accept()
            self.hide()
            if getattr(self, "tray_controller", None) and not self._tray_notified:
                self.tray_controller.notify_minimized()
                self._tray_notified = True
            return
        super().changeEvent(event)

    def closeEvent(self, event):
        if self._allow_close:
            event.accept()
            return
        self.hide()
        if getattr(self, "tray_controller", None):
            self.tray_controller.notify_minimized()
            self._tray_notified = True
        event.ignore()

    def _build_ui(self):
        central = QWidget(self)
        central.setObjectName("centralSurface")
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(18)

        hero_card = QFrame()
        hero_card.setObjectName("heroCard")
        hero_layout = QVBoxLayout(hero_card)
        hero_layout.setContentsMargins(22, 20, 22, 20)
        hero_layout.setSpacing(10)
        self.hero_title = QLabel("Memo Tasker")
        self.hero_title.setObjectName("heroTitle")
        self.hero_subtitle = QLabel("记录、排序和轮播你的工作任务，始终把最早到期的事项放在前面。")
        self.hero_subtitle.setWordWrap(True)
        self.hero_subtitle.setObjectName("heroSubtitle")
        hero_layout.addWidget(self.hero_title)
        hero_layout.addWidget(self.hero_subtitle)
        root_layout.addWidget(hero_card)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.pending_stat = self._build_stat_card("待办任务", "0")
        self.completed_stat = self._build_stat_card("已完成", "0")
        self.today_stat = self._build_stat_card("今天到期", "0")
        stats_row.addWidget(self.pending_stat[0], 1)
        stats_row.addWidget(self.completed_stat[0], 1)
        stats_row.addWidget(self.today_stat[0], 1)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(18)
        left_column = QVBoxLayout()
        left_column.setSpacing(16)
        right_column = QVBoxLayout()
        right_column.setSpacing(16)

        left_column.addLayout(stats_row)

        form_group = QGroupBox("新建任务")
        form_group.setObjectName("cardGroup")
        form_layout = QVBoxLayout(form_group)
        fields = QFormLayout()
        fields.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        fields.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        fields.setSpacing(10)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("输入任务标题")
        self.due_input = QDateTimeEdit(datetime.now())
        self.due_input.setCalendarPopup(True)
        self.due_input.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("#report #meeting")

        fields.addRow("标题", self.title_input)
        fields.addRow("截止时间", self.due_input)
        fields.addRow("标签", self.tags_input)
        form_layout.addLayout(fields)

        button_row = QHBoxLayout()
        self.submit_button = QPushButton("添加任务")
        self.submit_button.setObjectName("primaryButton")
        self.submit_button.clicked.connect(self.submit_task)
        self.cancel_edit_button = QPushButton("取消编辑")
        self.cancel_edit_button.setObjectName("secondaryButton")
        self.cancel_edit_button.clicked.connect(self.reset_form)
        self.cancel_edit_button.setEnabled(False)
        button_row.addWidget(self.submit_button)
        button_row.addWidget(self.cancel_edit_button)
        button_row.addStretch()
        form_layout.addLayout(button_row)

        helper_card = QFrame()
        helper_card.setObjectName("helperCard")
        helper_layout = QVBoxLayout(helper_card)
        helper_layout.setContentsMargins(18, 18, 18, 18)
        helper_layout.setSpacing(8)
        helper_title = QLabel("录入提示")
        helper_title.setObjectName("helperTitle")
        helper_text = QLabel(
            "标题尽量短，标签直接写成 #report #meeting。右侧设置会立刻同步到角落悬浮窗。"
        )
        helper_text.setObjectName("helperText")
        helper_text.setWordWrap(True)
        helper_layout.addWidget(helper_title)
        helper_layout.addWidget(helper_text)

        task_group = QGroupBox("任务列表")
        task_group.setObjectName("cardGroup")
        task_layout = QVBoxLayout(task_group)
        filter_row = QHBoxLayout()
        self.status_filter = QComboBox()
        self.status_filter.addItems(["全部", "未完成", "已完成"])
        self.status_filter.currentIndexChanged.connect(self.refresh_tasks)
        self.tag_filter = QComboBox()
        self.tag_filter.currentIndexChanged.connect(self.refresh_tasks)
        filter_row.addWidget(QLabel("状态"))
        filter_row.addWidget(self.status_filter)
        filter_row.addWidget(QLabel("标签"))
        filter_row.addWidget(self.tag_filter)
        filter_row.addStretch()
        task_layout.addLayout(filter_row)

        self.task_table = QTableWidget(0, 5)
        self.task_table.setObjectName("taskTable")
        self.task_table.setHorizontalHeaderLabels(["状态", "标题", "截止时间", "标签", "操作"])
        self.task_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setShowGrid(False)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.verticalHeader().setDefaultSectionSize(58)
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        task_layout.addWidget(self.task_table)
        left_column.addWidget(task_group, 1)

        settings_group = QGroupBox("悬浮窗设置")
        settings_group.setObjectName("cardGroup")
        settings_layout = QFormLayout(settings_group)
        self.corner_combo = QComboBox()
        self.corner_combo.addItem("右下角", "bottom-right")
        self.corner_combo.addItem("左下角", "bottom-left")
        self.corner_combo.addItem("右上角", "top-right")
        self.corner_combo.addItem("左上角", "top-left")
        self.corner_combo.currentIndexChanged.connect(self.save_settings_from_controls)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(35, 95)
        self.opacity_slider.valueChanged.connect(self.save_settings_from_controls)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(3, 120)
        self.interval_spin.setSuffix(" 秒")
        self.interval_spin.valueChanged.connect(self.save_settings_from_controls)

        self.click_through_checkbox = QCheckBox("点击穿透")
        self.click_through_checkbox.stateChanged.connect(self.save_settings_from_controls)
        self.always_on_top_checkbox = QCheckBox("置顶")
        self.always_on_top_checkbox.stateChanged.connect(self.save_settings_from_controls)
        self.paused_checkbox = QCheckBox("暂停轮播")
        self.paused_checkbox.stateChanged.connect(self.save_settings_from_controls)

        check_row = QHBoxLayout()
        check_row.addWidget(self.always_on_top_checkbox)
        check_row.addWidget(self.click_through_checkbox)
        check_row.addWidget(self.paused_checkbox)
        check_row.addStretch()

        export_button = QPushButton("立即导出今日完成")
        export_button.setObjectName("secondaryButton")
        export_button.clicked.connect(self.export_today)

        settings_layout.addRow("位置", self.corner_combo)
        settings_layout.addRow("透明度", self.opacity_slider)
        settings_layout.addRow("轮播间隔", self.interval_spin)
        settings_layout.addRow("行为", check_row)
        settings_layout.addRow("导出", export_button)

        right_column.addWidget(form_group)
        right_column.addWidget(helper_card)
        right_column.addWidget(settings_group)
        right_column.addStretch()

        body_layout.addLayout(left_column, 7)
        body_layout.addLayout(right_column, 4)
        root_layout.addLayout(body_layout, 1)

    def _apply_styles(self):
        self.setStyleSheet(
            """
            QWidget#centralSurface {
                background: #f3efe7;
            }
            QFrame#heroCard, QGroupBox#cardGroup, QFrame[statCard='true'], QFrame#helperCard {
                background: #fffaf1;
                border: 1px solid #e6dcc8;
                border-radius: 18px;
            }
            QFrame#heroCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #fff7ea, stop:0.55 #f7efe1, stop:1 #efe2cd);
            }
            QLabel#heroTitle {
                color: #2f2419;
                font-family: "Microsoft YaHei UI";
                font-size: 30px;
                font-weight: 700;
            }
            QLabel#heroSubtitle {
                color: #6e5b43;
                font-family: "Microsoft YaHei UI";
                font-size: 13px;
            }
            QLabel#helperTitle {
                color: #3e2b1a;
                font-family: "Microsoft YaHei UI";
                font-size: 15px;
                font-weight: 700;
            }
            QLabel#helperText {
                color: #6f5b43;
                font-family: "Microsoft YaHei UI";
                font-size: 12px;
                line-height: 1.5;
            }
            QGroupBox#cardGroup {
                margin-top: 12px;
                padding-top: 12px;
                font-family: "Microsoft YaHei UI";
                font-size: 13px;
                font-weight: 700;
                color: #46311d;
            }
            QGroupBox#cardGroup::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 6px;
            }
            QLabel[statRole='caption'] {
                color: #7f6a52;
                font-family: "Microsoft YaHei UI";
                font-size: 12px;
            }
            QLabel[statRole='value'] {
                color: #2b2318;
                font-family: "Microsoft YaHei UI";
                font-size: 28px;
                font-weight: 700;
            }
            QLineEdit, QDateTimeEdit, QComboBox, QSpinBox {
                background: #fffdf8;
                color: #2c2418;
                border: 1px solid #d8ccb8;
                border-radius: 10px;
                padding: 9px 12px;
                font-family: "Microsoft YaHei UI";
                font-size: 13px;
                min-height: 20px;
            }
            QLineEdit:focus, QDateTimeEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #b36b32;
            }
            QPushButton {
                border-radius: 10px;
                padding: 10px 14px;
                font-family: "Microsoft YaHei UI";
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#primaryButton {
                background: #1f6f63;
                color: white;
                border: none;
            }
            QPushButton#primaryButton:hover {
                background: #215c53;
            }
            QPushButton#secondaryButton {
                background: #f8f1e5;
                color: #5a4027;
                border: 1px solid #dccbb2;
            }
            QPushButton#secondaryButton:hover {
                background: #f0e5d5;
            }
            QPushButton#actionButton {
                background: #f8f1e5;
                color: #5a4027;
                border: 1px solid #dccbb2;
                border-radius: 9px;
                padding: 4px 10px;
                font-family: "Microsoft YaHei UI";
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton#actionButton:hover {
                background: #eddfc8;
                border-color: #c8a97a;
            }
            QTableWidget#taskTable {
                background: #fffdf9;
                alternate-background-color: #faf3e7;
                border: 1px solid #e0d3be;
                border-radius: 12px;
                color: #2f2419;
                gridline-color: transparent;
                selection-background-color: #ead8bc;
                font-family: "Microsoft YaHei UI";
                font-size: 13px;
            }
            QTableWidget#taskTable::item {
                padding: 8px;
            }
            QHeaderView::section {
                background: #efe3cf;
                color: #5c4630;
                border: none;
                border-bottom: 1px solid #deceb5;
                padding: 10px;
                font-family: "Microsoft YaHei UI";
                font-size: 12px;
                font-weight: 700;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #e6dccd;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #1f6f63;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QCheckBox {
                color: #4f3d2b;
                font-family: "Microsoft YaHei UI";
                font-size: 13px;
            }
            QComboBox::drop-down, QDateTimeEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: right center;
                width: 28px;
                border: none;
                border-left: 1px solid #d8ccb8;
                border-top-right-radius: 9px;
                border-bottom-right-radius: 9px;
                background: #ede5d6;
            }
            QComboBox::drop-down:hover, QDateTimeEdit::drop-down:hover {
                background: #e4d9c6;
            }
            QComboBox::down-arrow, QDateTimeEdit::down-arrow {
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #8a6545;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                subcontrol-origin: padding;
                width: 22px;
                border: none;
                border-left: 1px solid #d8ccb8;
                background: #ede5d6;
            }
            QSpinBox::up-button {
                subcontrol-position: right top;
                border-top-right-radius: 9px;
                border-bottom: 1px solid #d8ccb8;
            }
            QSpinBox::down-button {
                subcontrol-position: right bottom;
                border-bottom-right-radius: 9px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #e4d9c6;
            }
            QSpinBox::up-arrow {
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 5px solid #8a6545;
            }
            QSpinBox::down-arrow {
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #8a6545;
            }
            """
        )

    def _build_stat_card(self, caption: str, initial_value: str):
        card = QFrame()
        card.setProperty("statCard", True)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(68, 44, 18, 24))
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        caption_label = QLabel(caption)
        caption_label.setProperty("statRole", "caption")
        value_label = QLabel(initial_value)
        value_label.setProperty("statRole", "value")

        layout.addWidget(caption_label)
        layout.addWidget(value_label)
        return card, value_label

    def refresh_tasks(self):
        status_map = {"全部": None, "未完成": "pending", "已完成": "completed"}
        selected_status = status_map[self.status_filter.currentText()]
        selected_tag = self.tag_filter.currentData() if self.tag_filter.count() else None
        tasks = self.storage.list_tasks(status=selected_status, tag=selected_tag)
        all_tasks = self.storage.list_tasks()
        now = datetime.now()
        pending_count = len([task for task in all_tasks if task.status == "pending"])
        completed_count = len([task for task in all_tasks if task.status == "completed"])
        due_today_count = len(
            [task for task in all_tasks if task.status == "pending" and task.due_at and task.due_at.date() == now.date()]
        )
        self.pending_stat[1].setText(str(pending_count))
        self.completed_stat[1].setText(str(completed_count))
        self.today_stat[1].setText(str(due_today_count))

        self.task_table.setRowCount(len(tasks))
        for row_index, task in enumerate(tasks):
            status_text = "已完成" if task.status == "completed" else "未完成"
            if task.status == "completed" and task.completed_at:
                status_text = f"已完成 {task.completed_at.strftime('%H:%M')}"
            due_text = task.due_at.strftime("%Y-%m-%d %H:%M") if task.due_at else "未设置"
            tags_text = " ".join(task.tags)

            status_item = QTableWidgetItem(status_text)
            title_item = QTableWidgetItem(task.title)
            due_item = QTableWidgetItem(due_text)
            tags_item = QTableWidgetItem(tags_text)
            status_item.setTextAlignment(Qt.AlignCenter)
            due_item.setTextAlignment(Qt.AlignCenter)
            tags_item.setTextAlignment(Qt.AlignCenter)

            self.task_table.setItem(row_index, 0, status_item)
            self.task_table.setItem(row_index, 1, title_item)
            self.task_table.setItem(row_index, 2, due_item)
            self.task_table.setItem(row_index, 3, tags_item)
            self.task_table.setCellWidget(row_index, 4, self._build_actions(task.id, task.status))

        self._refresh_tag_filter()

    def _refresh_tag_filter(self):
        current_tag = self.tag_filter.currentData() if self.tag_filter.count() else None
        all_tags = sorted({tag for task in self.storage.list_tasks() for tag in task.tags})
        self.tag_filter.blockSignals(True)
        self.tag_filter.clear()
        self.tag_filter.addItem("全部标签", None)
        for tag in all_tags:
            self.tag_filter.addItem(tag, tag)
        index = self.tag_filter.findData(current_tag)
        self.tag_filter.setCurrentIndex(index if index >= 0 else 0)
        self.tag_filter.blockSignals(False)

    def _build_actions(self, task_id: int, status: str):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        def _btn(label: str) -> QPushButton:
            b = QPushButton(label)
            b.setObjectName("actionButton")
            b.setMinimumWidth(52)
            b.setFixedHeight(36)
            return b

        if status != "completed":
            complete_button = _btn("完成")
            complete_button.clicked.connect(lambda: self.complete_task(task_id))
            layout.addWidget(complete_button)

        edit_button = _btn("编辑")
        edit_button.clicked.connect(lambda: self.load_task_into_form(task_id))
        delete_button = _btn("删除")
        delete_button.clicked.connect(lambda: self.delete_task(task_id))
        layout.addWidget(edit_button)
        layout.addWidget(delete_button)
        return container

    def submit_task(self):
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "提示", "标题不能为空")
            return
        due_at = self.due_input.dateTime().toPython()
        tags = self._normalize_tags(self.tags_input.text())

        if self.editing_task_id is None:
            self.storage.add_task(title, due_at, tags)
        else:
            self.storage.update_task(self.editing_task_id, title, due_at, tags)

        self.reset_form()
        self.refresh_tasks()
        self.tasks_changed.emit()

    def load_task_into_form(self, task_id: int):
        task = self.storage.get_task(task_id)
        self.editing_task_id = task_id
        self.title_input.setText(task.title)
        if task.due_at:
            self.due_input.setDateTime(task.due_at)
        self.tags_input.setText(" ".join(task.tags))
        self.submit_button.setText("保存修改")
        self.cancel_edit_button.setEnabled(True)

    def reset_form(self):
        self.editing_task_id = None
        self.title_input.clear()
        self.tags_input.clear()
        self.due_input.setDateTime(datetime.now())
        self.submit_button.setText("添加任务")
        self.cancel_edit_button.setEnabled(False)

    def complete_task(self, task_id: int):
        self.storage.complete_task(task_id)
        self.refresh_tasks()
        self.tasks_changed.emit()
        self.task_completed.emit(task_id)

    def delete_task(self, task_id: int):
        answer = QMessageBox.question(self, "确认删除", "确定要删除这个任务吗？")
        if answer != QMessageBox.Yes:
            return
        self.storage.delete_task(task_id)
        self.refresh_tasks()
        self.tasks_changed.emit()
        self.task_deleted.emit(task_id)

    def save_settings_from_controls(self):
        settings = self.storage.update_settings(
            {
                "corner": self.corner_combo.currentData(),
                "opacity": round(self.opacity_slider.value() / 100, 2),
                "interval_seconds": self.interval_spin.value(),
                "click_through": self.click_through_checkbox.isChecked(),
                "always_on_top": self.always_on_top_checkbox.isChecked(),
                "paused": self.paused_checkbox.isChecked(),
                "position": None,
            }
        )
        self.settings_changed.emit(settings)

    def _load_settings_into_controls(self):
        settings = self.storage.load_settings()
        corner_index = self.corner_combo.findData(settings["corner"])
        self.corner_combo.setCurrentIndex(corner_index if corner_index >= 0 else 0)
        self.opacity_slider.setValue(int(settings["opacity"] * 100))
        self.interval_spin.setValue(settings["interval_seconds"])
        self.click_through_checkbox.setChecked(settings["click_through"])
        self.always_on_top_checkbox.setChecked(settings["always_on_top"])
        self.paused_checkbox.setChecked(settings["paused"])

    def apply_settings_to_controls(self, settings: dict):
        self.corner_combo.blockSignals(True)
        self.opacity_slider.blockSignals(True)
        self.interval_spin.blockSignals(True)
        self.click_through_checkbox.blockSignals(True)
        self.always_on_top_checkbox.blockSignals(True)
        self.paused_checkbox.blockSignals(True)

        corner_index = self.corner_combo.findData(settings["corner"])
        self.corner_combo.setCurrentIndex(corner_index if corner_index >= 0 else 0)
        self.opacity_slider.setValue(int(settings["opacity"] * 100))
        self.interval_spin.setValue(settings["interval_seconds"])
        self.click_through_checkbox.setChecked(settings["click_through"])
        self.always_on_top_checkbox.setChecked(settings["always_on_top"])
        self.paused_checkbox.setChecked(settings["paused"])

        self.corner_combo.blockSignals(False)
        self.opacity_slider.blockSignals(False)
        self.interval_spin.blockSignals(False)
        self.click_through_checkbox.blockSignals(False)
        self.always_on_top_checkbox.blockSignals(False)
        self.paused_checkbox.blockSignals(False)

    def export_today(self):
        path = self.export_today_callback(force=True)
        QMessageBox.information(self, "已导出", f"导出完成：\n{path}")

    @staticmethod
    def _normalize_tags(raw_text: str) -> list[str]:
        tags = []
        for item in raw_text.replace("，", " ").replace(",", " ").split():
            normalized = item if item.startswith("#") else f"#{item}"
            if normalized not in tags:
                tags.append(normalized)
        return tags

"""
botyaraPAD - UI Widgets
Кастомные виджеты: список звуков, элемент звука, слайдер громкости и т.д.
"""

import os
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QSlider, QListWidget, QListWidgetItem, QMenu, QAction,
    QInputDialog, QMessageBox, QFileDialog, QAbstractItemView,
    QSizePolicy, QFrame, QLineEdit
)
from PyQt5.QtCore import (
    Qt, pyqtSignal, QSize, QMimeData, QUrl, QTimer
)
from PyQt5.QtGui import QFont, QIcon, QDragEnterEvent, QDropEvent

from sound_manager import SoundInfo, SUPPORTED_FORMATS


# ─── Константы стилей ────────────────────────────────────────────

DARK_THEME = """
    QWidget {
        background-color: #1e1e2e;
        color: #cdd6f4;
        font-family: "Segoe UI", "Noto Sans", sans-serif;
        font-size: 13px;
    }
    QMainWindow {
        background-color: #1e1e2e;
    }
    QPushButton {
        background-color: #313244;
        color: #cdd6f4;
        border: 1px solid #45475a;
        border-radius: 6px;
        padding: 6px 14px;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #45475a;
        border-color: #89b4fa;
    }
    QPushButton:pressed {
        background-color: #585b70;
    }
    QPushButton:disabled {
        background-color: #1e1e2e;
        color: #585b70;
        border-color: #313244;
    }
    QPushButton#stopAllBtn {
        background-color: #f38ba8;
        color: #1e1e2e;
        font-weight: bold;
        border: none;
    }
    QPushButton#stopAllBtn:hover {
        background-color: #eba0ac;
    }
    QPushButton#loopBtn {
        background-color: #313244;
        color: #cdd6f4;
        font-weight: bold;
    }
    QPushButton#loopBtn:checked {
        background-color: #a6e3a1;
        color: #1e1e2e;
    }
    QSlider::groove:horizontal {
        border: none;
        height: 6px;
        background: #313244;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #89b4fa;
        border: none;
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }
    QSlider::handle:horizontal:hover {
        background: #b4befe;
    }
    QSlider::sub-page:horizontal {
        background: #89b4fa;
        border-radius: 3px;
    }
    QLineEdit {
        background-color: #313244;
        color: #cdd6f4;
        border: 1px solid #45475a;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
    }
    QLineEdit:focus {
        border-color: #89b4fa;
    }
    QTabWidget::pane {
        border: 1px solid #45475a;
        border-radius: 6px;
        background-color: #1e1e2e;
    }
    QTabBar::tab {
        background-color: #313244;
        color: #cdd6f4;
        border: 1px solid #45475a;
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 6px 16px;
        margin-right: 2px;
        font-size: 13px;
    }
    QTabBar::tab:selected {
        background-color: #45475a;
        color: #89b4fa;
        font-weight: bold;
    }
    QTabBar::tab:hover:!selected {
        background-color: #3b3d50;
    }
    QListWidget {
        background-color: #181825;
        border: 1px solid #313244;
        border-radius: 6px;
        outline: none;
        padding: 4px;
    }
    QListWidget::item {
        background-color: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 6px;
        margin: 2px 0px;
        padding: 0px;
    }
    QListWidget::item:selected {
        background-color: #313244;
        border-color: #89b4fa;
    }
    QListWidget::item:hover:!selected {
        background-color: #262637;
        border-color: #45475a;
    }
    QScrollBar:vertical {
        background: #181825;
        width: 10px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical {
        background: #45475a;
        border-radius: 5px;
        min-height: 30px;
    }
    QScrollBar::handle:vertical:hover {
        background: #585b70;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }
    QMenu {
        background-color: #313244;
        color: #cdd6f4;
        border: 1px solid #45475a;
        border-radius: 6px;
        padding: 4px;
    }
    QMenu::item {
        padding: 6px 20px;
        border-radius: 4px;
    }
    QMenu::item:selected {
        background-color: #45475a;
    }
    QMenu::separator {
        height: 1px;
        background: #45475a;
        margin: 4px 8px;
    }
    QLabel#statusLabel {
        color: #a6adc8;
        font-size: 12px;
    }
    QLabel#titleLabel {
        color: #89b4fa;
        font-size: 16px;
        font-weight: bold;
    }
    QLabel#volumeLabel {
        color: #a6adc8;
        font-size: 12px;
    }
"""

LIGHT_THEME = """
    QWidget {
        background-color: #eff1f5;
        color: #4c4f69;
        font-family: "Segoe UI", "Noto Sans", sans-serif;
        font-size: 13px;
    }
    QMainWindow {
        background-color: #eff1f5;
    }
    QPushButton {
        background-color: #ccd0da;
        color: #4c4f69;
        border: 1px solid #bcc0cc;
        border-radius: 6px;
        padding: 6px 14px;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #bcc0cc;
        border-color: #1e66f5;
    }
    QPushButton:pressed {
        background-color: #acb0be;
    }
    QPushButton:disabled {
        background-color: #e6e9ef;
        color: #9ca0b0;
        border-color: #ccd0da;
    }
    QPushButton#stopAllBtn {
        background-color: #d20f39;
        color: #eff1f5;
        font-weight: bold;
        border: none;
    }
    QPushButton#stopAllBtn:hover {
        background-color: #e63e5c;
    }
    QPushButton#loopBtn {
        background-color: #ccd0da;
        color: #4c4f69;
        font-weight: bold;
    }
    QPushButton#loopBtn:checked {
        background-color: #40a02b;
        color: #eff1f5;
    }
    QSlider::groove:horizontal {
        border: none;
        height: 6px;
        background: #ccd0da;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #1e66f5;
        border: none;
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }
    QSlider::handle:horizontal:hover {
        background: #7287fd;
    }
    QSlider::sub-page:horizontal {
        background: #1e66f5;
        border-radius: 3px;
    }
    QLineEdit {
        background-color: #ccd0da;
        color: #4c4f69;
        border: 1px solid #bcc0cc;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
    }
    QLineEdit:focus {
        border-color: #1e66f5;
    }
    QTabWidget::pane {
        border: 1px solid #bcc0cc;
        border-radius: 6px;
        background-color: #eff1f5;
    }
    QTabBar::tab {
        background-color: #ccd0da;
        color: #4c4f69;
        border: 1px solid #bcc0cc;
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 6px 16px;
        margin-right: 2px;
        font-size: 13px;
    }
    QTabBar::tab:selected {
        background-color: #bcc0cc;
        color: #1e66f5;
        font-weight: bold;
    }
    QTabBar::tab:hover:!selected {
        background-color: #c4c8d4;
    }
    QListWidget {
        background-color: #e6e9ef;
        border: 1px solid #ccd0da;
        border-radius: 6px;
        outline: none;
        padding: 4px;
    }
    QListWidget::item {
        background-color: #eff1f5;
        border: 1px solid #ccd0da;
        border-radius: 6px;
        margin: 2px 0px;
        padding: 0px;
    }
    QListWidget::item:selected {
        background-color: #ccd0da;
        border-color: #1e66f5;
    }
    QListWidget::item:hover:!selected {
        background-color: #dce0e8;
        border-color: #bcc0cc;
    }
    QScrollBar:vertical {
        background: #e6e9ef;
        width: 10px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical {
        background: #bcc0cc;
        border-radius: 5px;
        min-height: 30px;
    }
    QScrollBar::handle:vertical:hover {
        background: #acb0be;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }
    QMenu {
        background-color: #ccd0da;
        color: #4c4f69;
        border: 1px solid #bcc0cc;
        border-radius: 6px;
        padding: 4px;
    }
    QMenu::item {
        padding: 6px 20px;
        border-radius: 4px;
    }
    QMenu::item:selected {
        background-color: #bcc0cc;
    }
    QMenu::separator {
        height: 1px;
        background: #bcc0cc;
        margin: 4px 8px;
    }
    QLabel#statusLabel {
        color: #6c6f85;
        font-size: 12px;
    }
    QLabel#titleLabel {
        color: #1e66f5;
        font-size: 16px;
        font-weight: bold;
    }
    QLabel#volumeLabel {
        color: #6c6f85;
        font-size: 12px;
    }
"""


def get_theme_stylesheet(theme_name: str) -> str:
    """Получить стиль по имени темы."""
    if theme_name == "light":
        return LIGHT_THEME
    return DARK_THEME


# ─── Виджет элемента звука ───────────────────────────────────────

class SoundItemWidget(QWidget):
    """Виджет одного звука в списке."""

    play_requested = pyqtSignal(int, str)       # (sound_index, play_mode)
    context_menu_requested = pyqtSignal(int)     # sound_index

    def __init__(self, sound_info: SoundInfo, index: int, parent=None):
        super().__init__(parent)
        self.sound_info = sound_info
        self.index = index
        self._is_playing = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        # Индикатор воспроизведения
        self.play_indicator = QLabel("▶")
        self.play_indicator.setFixedWidth(20)
        self.play_indicator.setAlignment(Qt.AlignCenter)
        self.play_indicator.setStyleSheet("color: #585b70; font-size: 14px;")
        layout.addWidget(self.play_indicator)

        # Название
        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)
        info_layout.setContentsMargins(0, 0, 0, 0)

        self.name_label = QLabel(self.sound_info.display_name)
        self.name_label.setFont(QFont("Noto Sans", 12, QFont.Normal))
        self.name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        info_layout.addWidget(self.name_label)

        # Подпись — оригинальное имя файла (если есть кастомное имя)
        if self.sound_info.custom_name:
            self.filename_label = QLabel(self.sound_info.filename)
            self.filename_label.setStyleSheet("color: #6c7086; font-size: 11px;")
            info_layout.addWidget(self.filename_label)
        else:
            self.filename_label = None

        layout.addLayout(info_layout, stretch=1)

        # Режим воспроизведения (иконка)
        mode_icons = {
            "both": "🔊🎤",
            "speaker": "🔊",
            "mic": "🎤"
        }
        mode_text = mode_icons.get(self.sound_info.play_mode, "🔊🎤")
        self.mode_label = QLabel(mode_text)
        self.mode_label.setFixedWidth(45)
        self.mode_label.setAlignment(Qt.AlignCenter)
        self.mode_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.mode_label)

        # Громкость
        self.volume_label = QLabel(f"{self.sound_info.volume}%")
        self.volume_label.setFixedWidth(40)
        self.volume_label.setAlignment(Qt.AlignCenter)
        self.volume_label.setObjectName("volumeLabel")
        layout.addWidget(self.volume_label)

        # Длительность
        self.duration_label = QLabel(self.sound_info.duration_str)
        self.duration_label.setFixedWidth(55)
        self.duration_label.setAlignment(Qt.AlignCenter)
        self.duration_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.duration_label)

        # Если файл не существует — подсвечиваем красным
        if not self.sound_info.exists:
            self.name_label.setStyleSheet("color: #f38ba8;")
            if self.filename_label:
                self.filename_label.setStyleSheet("color: #f38ba8; font-size: 11px;")

    def set_playing(self, playing: bool):
        """Установить индикатор воспроизведения."""
        self._is_playing = playing
        if playing:
            self.play_indicator.setStyleSheet("color: #a6e3a1; font-size: 14px;")
            self.play_indicator.setText("⏸")
        else:
            self.play_indicator.setStyleSheet("color: #585b70; font-size: 14px;")
            self.play_indicator.setText("▶")

    def update_duration(self):
        """Обновить отображение длительности."""
        self.duration_label.setText(self.sound_info.duration_str)

    def update_info(self):
        """Обновить всю информацию."""
        self.name_label.setText(self.sound_info.display_name)
        self.volume_label.setText(f"{self.sound_info.volume}%")
        self.duration_label.setText(self.sound_info.duration_str)

        mode_icons = {
            "both": "🔊🎤",
            "speaker": "🔊",
            "mic": "🎤"
        }
        self.mode_label.setText(mode_icons.get(self.sound_info.play_mode, "🔊🎤"))

        if self.filename_label:
            if self.sound_info.custom_name:
                self.filename_label.setText(self.sound_info.filename)
                self.filename_label.show()
            else:
                self.filename_label.hide()


# ─── Список звуков с Drag & Drop ─────────────────────────────────

class SoundListWidget(QListWidget):
    """
    Список звуков с поддержкой Drag & Drop файлов,
    контекстного меню и воспроизведения.
    """

    files_dropped = pyqtSignal(list)          # [filepath, ...]
    sound_play_requested = pyqtSignal(int, str)   # (sound_index, play_mode)
    sound_context_menu = pyqtSignal(int, object)  # (sound_index, QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSpacing(0)

        # Подключаем двойной клик и Enter
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    def keyPressEvent(self, event):
        """Обработка Enter для воспроизведения."""
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            current_row = self.currentRow()
            if current_row >= 0:
                self.sound_play_requested.emit(current_row, "both")
            return
        super().keyPressEvent(event)

    def _on_item_double_clicked(self, item):
        """Двойной клик — воспроизведение."""
        row = self.row(item)
        if row >= 0:
            self.sound_play_requested.emit(row, "both")

    def contextMenuEvent(self, event):
        """Контекстное меню."""
        item = self.itemAt(event.pos())
        if item is not None:
            row = self.row(item)
            self.sound_context_menu.emit(row, event.globalPos())
        else:
            # Клик по пустому месту — меню с добавлением
            self.sound_context_menu.emit(-1, event.globalPos())

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Принимаем drag с файлами."""
        if event.mimeData().hasUrls():
            # Проверяем что хоть один файл подходящего формата
            for url in event.mimeData().urls():
                filepath = url.toLocalFile()
                _, ext = os.path.splitext(filepath)
                if ext.lower() in SUPPORTED_FORMATS:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragMoveEvent(self, event):
        """Принимаем перемещение drag."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Обработка drop — добавление файлов."""
        if event.mimeData().hasUrls():
            files = []
            for url in event.mimeData().urls():
                filepath = url.toLocalFile()
                if os.path.isfile(filepath):
                    _, ext = os.path.splitext(filepath)
                    if ext.lower() in SUPPORTED_FORMATS:
                        files.append(filepath)
                elif os.path.isdir(filepath):
                    # Рекурсивно добавляем файлы из папки
                    for root, dirs, filenames in os.walk(filepath):
                        for fname in sorted(filenames):
                            fpath = os.path.join(root, fname)
                            _, ext = os.path.splitext(fpath)
                            if ext.lower() in SUPPORTED_FORMATS:
                                files.append(fpath)

            if files:
                self.files_dropped.emit(files)
                event.acceptProposedAction()
                return

        event.ignore()


# ─── Виджет верхней панели (громкость, поиск, кнопки) ────────────

class TopBarWidget(QWidget):
    """Верхняя панель: мастер-громкость, поиск, кнопки управления."""

    volume_changed = pyqtSignal(int)       # 0-100
    search_changed = pyqtSignal(str)
    stop_all_clicked = pyqtSignal()
    loop_toggled = pyqtSignal(bool)
    settings_clicked = pyqtSignal()
    add_sound_clicked = pyqtSignal()

    def __init__(self, initial_volume: int = 75, loop_enabled: bool = False, parent=None):
        super().__init__(parent)
        self._setup_ui(initial_volume, loop_enabled)

    def _setup_ui(self, initial_volume: int, loop_enabled: bool):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 4)
        main_layout.setSpacing(6)

        # ── Первая строка: заголовок + кнопки ──
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        title = QLabel("botyaraPAD")
        title.setObjectName("titleLabel")
        top_row.addWidget(title)

        top_row.addStretch()

        # Статус
        self.status_label = QLabel("⏹ Не активен")
        self.status_label.setObjectName("statusLabel")
        top_row.addWidget(self.status_label)

        top_row.addStretch()

        # Кнопка настроек
        self.settings_btn = QPushButton("⚙ Настройки")
        self.settings_btn.setFixedHeight(32)
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        top_row.addWidget(self.settings_btn)

        main_layout.addLayout(top_row)

        # ── Вторая строка: громкость ──
        volume_row = QHBoxLayout()
        volume_row.setSpacing(8)

        vol_icon = QLabel("🔊")
        vol_icon.setFixedWidth(24)
        volume_row.addWidget(vol_icon)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(initial_volume)
        self.volume_slider.setFixedHeight(24)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        volume_row.addWidget(self.volume_slider, stretch=1)

        self.volume_value_label = QLabel(f"{initial_volume}%")
        self.volume_value_label.setFixedWidth(40)
        self.volume_value_label.setAlignment(Qt.AlignCenter)
        self.volume_value_label.setObjectName("volumeLabel")
        volume_row.addWidget(self.volume_value_label)

        main_layout.addLayout(volume_row)

        # ── Третья строка: поиск + кнопки ──
        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)

        # Поиск
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск звуков...")
        self.search_input.setFixedHeight(32)
        self.search_input.textChanged.connect(self.search_changed.emit)
        self.search_input.setClearButtonEnabled(True)
        controls_row.addWidget(self.search_input, stretch=1)

        # Кнопка добавления
        self.add_btn = QPushButton("＋ Добавить")
        self.add_btn.setFixedHeight(32)
        self.add_btn.clicked.connect(self.add_sound_clicked.emit)
        controls_row.addWidget(self.add_btn)

        # Кнопка зацикливания
        self.loop_btn = QPushButton("🔁 Цикл")
        self.loop_btn.setObjectName("loopBtn")
        self.loop_btn.setCheckable(True)
        self.loop_btn.setChecked(loop_enabled)
        self.loop_btn.setFixedHeight(32)
        self.loop_btn.toggled.connect(self.loop_toggled.emit)
        controls_row.addWidget(self.loop_btn)

        # Кнопка остановки всех
        self.stop_all_btn = QPushButton("⏹ Стоп всё")
        self.stop_all_btn.setObjectName("stopAllBtn")
        self.stop_all_btn.setFixedHeight(32)
        self.stop_all_btn.clicked.connect(self.stop_all_clicked.emit)
        controls_row.addWidget(self.stop_all_btn)

        main_layout.addLayout(controls_row)

        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("color: #45475a;")
        main_layout.addWidget(separator)

    def _on_volume_changed(self, value: int):
        self.volume_value_label.setText(f"{value}%")
        self.volume_changed.emit(value)

    def set_status(self, text: str):
        """Установить текст статуса."""
        self.status_label.setText(text)

    def set_volume(self, value: int):
        """Установить громкость (без сигнала)."""
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(value)
        self.volume_value_label.setText(f"{value}%")
        self.volume_slider.blockSignals(False)

    def set_loop(self, enabled: bool):
        """Установить состояние зацикливания (без сигнала)."""
        self.loop_btn.blockSignals(True)
        self.loop_btn.setChecked(enabled)
        self.loop_btn.blockSignals(False)


# ─── Диалог редактирования звука ─────────────────────────────────

class SoundEditDialog(QWidget):
    """Не диалог, а просто набор статических методов для редактирования."""

    @staticmethod
    def edit_custom_name(parent, current_name: str) -> str:
        """Диалог ввода кастомного имени. Возвращает новое имя или пустую строку."""
        text, ok = QInputDialog.getText(
            parent,
            "Кастомное название",
            "Введите новое название (оставьте пустым для сброса):",
            QLineEdit.Normal,
            current_name
        )
        if ok:
            return text.strip()
        return current_name

    @staticmethod
    def edit_volume(parent, current_volume: int) -> int:
        """Диалог изменения громкости. Возвращает новую громкость."""
        value, ok = QInputDialog.getInt(
            parent,
            "Громкость звука",
            "Громкость (0-100):",
            current_volume,
            0, 100, 5
        )
        if ok:
            return value
        return current_volume

    @staticmethod
    def choose_play_mode(parent) -> str:
        """Выбор режима воспроизведения. Возвращает режим или пустую строку."""
        items = [
            "🔊🎤 Динамик + Микрофон",
            "🔊 Только динамик",
            "🎤 Только микрофон"
        ]
        item, ok = QInputDialog.getItem(
            parent,
            "Режим воспроизведения",
            "Выберите режим:",
            items, 0, False
        )
        if ok:
            if "Динамик + Микрофон" in item:
                return "both"
            elif "Только динамик" in item:
                return "speaker"
            elif "Только микрофон" in item:
                return "mic"
        return ""

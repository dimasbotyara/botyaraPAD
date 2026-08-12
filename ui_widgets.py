"""
botyaraPAD - UI Widgets
Кастомные виджеты: список звуков, элемент звука, слайдер громкости и т.д.
"""

import os
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QSlider, QListWidget, QListWidgetItem, QMenu, QAction,
    QInputDialog, QMessageBox, QFileDialog, QAbstractItemView,
    QSizePolicy, QFrame, QLineEdit, QDialog, QDialogButtonBox,
    QProgressBar
)
from PyQt5.QtCore import (
    Qt, pyqtSignal, QSize, QMimeData, QUrl, QTimer, QPoint
)
from PyQt5.QtGui import QFont, QIcon, QDragEnterEvent, QDropEvent, QKeyEvent, QPalette, QColor

from sound_manager import SoundInfo, SUPPORTED_FORMATS, format_keybind


# ─── Константы стилей ────────────────────────────────────────────

DARK_THEME = """
    QWidget {
        background-color: #1e1e2e;
        color: #cdd6f4;
        font-family: "Noto Sans", "Segoe UI", "Noto Color Emoji", "Noto Sans Symbols 2", "Noto Sans Symbols", "Segoe UI Emoji", "Apple Color Emoji", "DejaVu Sans", sans-serif;
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
    QProgressBar#soundProgress {
        background-color: #313244;
        border: none;
        border-radius: 2px;
        max-height: 4px;
        min-height: 4px;
    }
    QProgressBar#soundProgress::chunk {
        background-color: #89b4fa;
        border-radius: 2px;
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
    QLabel#keybindLabel {
        color: #f9e2af;
        font-size: 11px;
        background-color: #45475a;
        border-radius: 3px;
        padding: 2px 6px;
    }
"""

LIGHT_THEME = """
    QWidget {
        background-color: #eff1f5;
        color: #4c4f69;
        font-family: "Noto Sans", "Segoe UI", "Noto Color Emoji", "Noto Sans Symbols 2", "Noto Sans Symbols", "Segoe UI Emoji", "Apple Color Emoji", "DejaVu Sans", sans-serif;
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
    QProgressBar#soundProgress {
        background-color: #ccd0da;
        border: none;
        border-radius: 2px;
        max-height: 4px;
        min-height: 4px;
    }
    QProgressBar#soundProgress::chunk {
        background-color: #1e66f5;
        border-radius: 2px;
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
    QLabel#keybindLabel {
        color: #df8e1d;
        font-size: 11px;
        background-color: #bcc0cc;
        border-radius: 3px;
        padding: 2px 6px;
    }
"""


def get_theme_stylesheet(theme_name: str) -> str:
    """Получить стиль по имени темы."""
    if theme_name == "light":
        return LIGHT_THEME
    return DARK_THEME


# ─── Виджет элемента звука ───────────────────────────────────────

class SoundItemWidget(QWidget):
    """Виджет одного звука в списке с кнопками Play, Pause, Stop и шкалой прогресса."""

    play_requested = pyqtSignal(int, str)        # (sound_index, play_mode)
    pause_requested = pyqtSignal(int)            # sound_index
    stop_requested = pyqtSignal(int)             # sound_index
    context_menu_requested = pyqtSignal(int)     # sound_index

    def __init__(self, sound_info: SoundInfo, index: int, parent=None):
        super().__init__(parent)
        self.sound_info = sound_info
        self.index = index
        self._is_playing = False
        self._is_paused = False
        self._setup_ui()

    def _setup_ui(self):
        main_vbox = QVBoxLayout(self)
        main_vbox.setContentsMargins(8, 6, 8, 6)
        main_vbox.setSpacing(4)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)

        # Кнопка Play/Pause (▶ / ⏸)
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(26, 26)
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setToolTip("Воспроизвести / Пауза")
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #a6e3a1;
                border: 1px solid #45475a;
                border-radius: 13px;
                font-size: 12px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #45475a;
                border-color: #a6e3a1;
            }
        """)
        self.play_btn.clicked.connect(self._on_play_btn_clicked)
        top_layout.addWidget(self.play_btn)

        # Кнопка Stop (⏹)
        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setFixedSize(26, 26)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setToolTip("Остановить звук")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #f38ba8;
                border: 1px solid #45475a;
                border-radius: 13px;
                font-size: 11px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #f38ba8;
                color: #1e1e2e;
                border-color: #f38ba8;
            }
        """)
        self.stop_btn.clicked.connect(self._on_stop_btn_clicked)
        top_layout.addWidget(self.stop_btn)

        # Название и информация
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setContentsMargins(0, 0, 0, 0)

        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        name_row.setContentsMargins(0, 0, 0, 0)

        self.name_label = QLabel(self.sound_info.display_name)
        self.name_label.setFont(QFont("Noto Sans", 11, QFont.Normal))
        self.name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        name_row.addWidget(self.name_label)

        if self.sound_info.keybind:
            self.keybind_label = QLabel(self.sound_info.keybind)
            self.keybind_label.setObjectName("keybindLabel")
            self.keybind_label.setAlignment(Qt.AlignCenter)
            self.keybind_label.setFixedHeight(18)
            name_row.addWidget(self.keybind_label)
        else:
            self.keybind_label = None

        info_layout.addLayout(name_row)

        if self.sound_info.custom_name:
            self.filename_label = QLabel(self.sound_info.filename)
            self.filename_label.setStyleSheet("color: #6c7086; font-size: 11px;")
            info_layout.addWidget(self.filename_label)
        else:
            self.filename_label = None

        top_layout.addLayout(info_layout, stretch=1)

        # Режим воспроизведения
        mode_icons = {"both": "🔊🎤", "speaker": "🔊", "mic": "🎤"}
        self.mode_label = QLabel(mode_icons.get(self.sound_info.play_mode, "🔊🎤"))
        self.mode_label.setFixedWidth(40)
        self.mode_label.setAlignment(Qt.AlignCenter)
        self.mode_label.setStyleSheet("font-size: 13px;")
        top_layout.addWidget(self.mode_label)

        # Громкость
        self.volume_label = QLabel(f"{self.sound_info.volume}%")
        self.volume_label.setFixedWidth(38)
        self.volume_label.setAlignment(Qt.AlignCenter)
        self.volume_label.setObjectName("volumeLabel")
        top_layout.addWidget(self.volume_label)

        # Длительность / Время
        self.duration_label = QLabel(self.sound_info.duration_str)
        self.duration_label.setFixedWidth(85)
        self.duration_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.duration_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #a6adc8;")
        top_layout.addWidget(self.duration_label)

        main_vbox.addLayout(top_layout)

        # Прогрессбар воспроизведения
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("soundProgress")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.hide()
        main_vbox.addWidget(self.progress_bar)

        if not self.sound_info.exists:
            self.name_label.setStyleSheet("color: #f38ba8;")
            if self.filename_label:
                self.filename_label.setStyleSheet("color: #f38ba8; font-size: 11px;")

    def _on_play_btn_clicked(self):
        if self._is_playing and not self._is_paused:
            self.pause_requested.emit(self.index)
        else:
            self.play_requested.emit(self.index, "default")

    def _on_stop_btn_clicked(self):
        self.stop_requested.emit(self.index)

    def set_playback_progress(self, elapsed: float, duration: float, is_paused: bool = False):
        """Обновить шкалу прогресса и индикатор времени."""
        self._is_playing = True
        self._is_paused = is_paused

        if not self.progress_bar.isVisible():
            self.progress_bar.show()

        if duration > 0:
            pct = int(min(100, max(0, (elapsed / duration) * 100)))
            self.progress_bar.setValue(pct)

        from sound_manager import format_duration
        elapsed_str = format_duration(elapsed)
        dur_str = format_duration(duration) if duration > 0 else self.sound_info.duration_str

        status_tag = "⏸ " if is_paused else ""
        self.duration_label.setText(f"{status_tag}{elapsed_str}/{dur_str}")
        self.duration_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #a6e3a1;" if not is_paused else "font-size: 11px; font-weight: bold; color: #f9e2af;")

        self.play_btn.setText("▶" if is_paused else "⏸")
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #45475a;
                color: %s;
                border: 1px solid %s;
                border-radius: 13px;
                font-size: 12px;
                font-weight: bold;
            }
        """ % ("#f9e2af" if is_paused else "#a6e3a1", "#f9e2af" if is_paused else "#a6e3a1"))

    def set_stopped(self):
        """Сбросить виджет в состояние «остановлен»."""
        self._is_playing = False
        self._is_paused = False
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.duration_label.setText(self.sound_info.duration_str)
        self.duration_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #a6adc8;")
        self.play_btn.setText("▶")
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #a6e3a1;
                border: 1px solid #45475a;
                border-radius: 13px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45475a;
                border-color: #a6e3a1;
            }
        """)

    def set_playing(self, playing: bool):
        """Установить индикатор воспроизведения."""
        if not playing:
            self.set_stopped()
        else:
            self._is_playing = True
            self.play_btn.setText("⏸")

    def update_duration(self):
        """Обновить отображение длительности."""
        if not self._is_playing:
            self.duration_label.setText(self.sound_info.duration_str)

    def update_info(self):
        """Обновить всю информацию."""
        self.name_label.setText(self.sound_info.display_name)
        self.volume_label.setText(f"{self.sound_info.volume}%")
        if not self._is_playing:
            self.duration_label.setText(self.sound_info.duration_str)

        mode_icons = {"both": "🔊🎤", "speaker": "🔊", "mic": "🎤"}
        self.mode_label.setText(mode_icons.get(self.sound_info.play_mode, "🔊🎤"))

        if self.sound_info.keybind:
            if self.keybind_label is None:
                self.keybind_label = QLabel(self.sound_info.keybind)
                self.keybind_label.setObjectName("keybindLabel")
                self.keybind_label.setAlignment(Qt.AlignCenter)
                self.keybind_label.setFixedHeight(18)
                main_vbox = self.layout()
                top_layout = main_vbox.itemAt(0).layout()
                info_layout = top_layout.itemAt(2).layout()
                name_row = info_layout.itemAt(0).layout()
                name_row.addWidget(self.keybind_label)
            else:
                self.keybind_label.setText(self.sound_info.keybind)
                self.keybind_label.show()
        else:
            if self.keybind_label is not None:
                self.keybind_label.hide()

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
    контекстного меню, воспроизведения и перестановки.
    """

    files_dropped = pyqtSignal(list)          # [filepath, ...]
    sound_play_requested = pyqtSignal(int, str)   # (sound_index, play_mode)
    sound_pause_requested = pyqtSignal(int)      # sound_index
    sound_stop_requested = pyqtSignal(int)       # sound_index
    sound_context_menu = pyqtSignal(int, object)  # (sound_index, QPoint)
    sounds_reordered = pyqtSignal(int, int)       # (from_index, to_index)
    selection_changed = pyqtSignal(list)          # [sound_indices]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)  # Множественное выделение
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSpacing(0)
        self.setDefaultDropAction(Qt.MoveAction)

        # Подключаем двойной клик и Enter
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self):
        """Уведомить о изменении выделения."""
        indices = [self.row(item) for item in self.selectedItems()]
        self.selection_changed.emit(indices)

    def keyPressEvent(self, event: QKeyEvent):
        """Обработка клавиш."""
        # Enter/Return — воспроизведение
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            current_row = self.currentRow()
            if current_row >= 0:
                self.sound_play_requested.emit(current_row, "both")
            return

        # Delete — удаление (обрабатывается в main window)

        # Ctrl+A — выделить все
        if event.key() == Qt.Key_A and event.modifiers() == Qt.ControlModifier:
            self.selectAll()
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
        """Принимаем drag с файлами или внутренний drag."""
        if event.source() == self:
            # Внутреннее перемещение
            event.acceptProposedAction()
        elif event.mimeData().hasUrls():
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
        if event.source() == self or event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Обработка drop."""
        if event.source() == self:
            # Внутреннее перемещение
            drop_row = self.indexAt(event.pos()).row()
            if drop_row < 0:
                drop_row = self.count()

            selected_rows = sorted([self.row(item) for item in self.selectedItems()])
            if not selected_rows:
                event.ignore()
                return

            # Перемещаем выбранные элементы
            for i, from_row in enumerate(selected_rows):
                # Корректируем индекс если перемещаем вниз
                actual_from = from_row
                actual_to = drop_row + i if drop_row > from_row else drop_row + i

                self.sounds_reordered.emit(actual_from, actual_to)

            event.acceptProposedAction()

        elif event.mimeData().hasUrls():
            # Добавление файлов
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


# ─── Виджет верхней панели ────────────────────────────────────────

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
        self.add_btn = QPushButton("➕ Добавить")
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


# ─── Диалоги редактирования ──────────────────────────────────────

class KeybindDialog(QDialog):
    """Диалог для записи биндинга клавиш."""

    def __init__(self, current_keybind: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Установить биндинг")
        self.setModal(True)
        self.setFixedSize(400, 150)

        self.recorded_keys = set()
        self.keybind_str = current_keybind

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info_label = QLabel("Нажмите комбинацию клавиш (например Ctrl+Shift+A)")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        self.display_label = QLabel(current_keybind or "(нажмите клавиши)")
        self.display_label.setAlignment(Qt.AlignCenter)
        self.display_label.setStyleSheet(
            "QLabel { background-color: #313244; border: 1px solid #45475a; "
            "border-radius: 6px; padding: 12px; font-size: 14px; font-weight: bold; }"
        )
        layout.addWidget(self.display_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        clear_btn = QPushButton("Очистить")
        clear_btn.clicked.connect(self._clear)
        buttons.addButton(clear_btn, QDialogButtonBox.ResetRole)

        layout.addWidget(buttons)

        self.setFocus()

    def keyPressEvent(self, event: QKeyEvent):
        """Запись нажатых клавиш."""
        key = event.key()

        # Игнорируем модификаторы отдельно
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            return

        # Собираем модификаторы
        modifiers = []
        if event.modifiers() & Qt.ControlModifier:
            modifiers.append("Ctrl")
        if event.modifiers() & Qt.ShiftModifier:
            modifiers.append("Shift")
        if event.modifiers() & Qt.AltModifier:
            modifiers.append("Alt")
        if event.modifiers() & Qt.MetaModifier:
            modifiers.append("Super")

        # Получаем имя клавиши через QKeySequence
        key_name = QKeySequence(key).toString()
        if key_name and key_name not in modifiers:
            parts = modifiers + [key_name]
            self.keybind_str = "+".join(parts)
            self.display_label.setText(self.keybind_str)

    def _clear(self):
        """Очистить биндинг."""
        self.keybind_str = ""
        self.display_label.setText("(нажмите клавиши)")

    def get_keybind(self) -> str:
        """Получить записанный биндинг."""
        return self.keybind_str


class SoundEditDialog:
    """Не диалог, а просто набор статических методов для редактирования."""

    @staticmethod
    def edit_custom_name(parent, current_name: str) -> str:
        """Диалог ввода кастомного имени."""
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
        """Диалог изменения громкости."""
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
        """Выбор режима воспроизведения."""
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

    @staticmethod
    def edit_keybind(parent, current_keybind: str) -> str:
        """Диалог установки биндинга."""
        dialog = KeybindDialog(current_keybind, parent)
        if dialog.exec_() == QDialog.Accepted:
            return dialog.get_keybind()
        return current_keybind

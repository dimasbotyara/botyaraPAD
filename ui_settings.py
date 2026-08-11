"""
botyaraPAD - Settings Window
Окно настроек приложения.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QCheckBox, QLineEdit, QGroupBox, QFormLayout,
    QSpacerItem, QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal

from config_manager import ConfigManager
from audio_engine import PipeWireVirtualMic


class SettingsWindow(QDialog):
    """Окно настроек botyaraPAD."""

    settings_applied = pyqtSignal()  # Сигнал о применении настроек
    theme_changed = pyqtSignal(str)  # Сигнал о смене темы

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("botyaraPAD — Настройки")
        self.setMinimumWidth(500)
        self.setMinimumHeight(450)
        self.setModal(True)

        self._sources_cache = []
        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── Группа: Виртуальный микрофон ──
        mic_group = QGroupBox("🎤 Виртуальный микрофон")
        mic_form = QFormLayout(mic_group)
        mic_form.setSpacing(8)

        self.device_name_input = QLineEdit()
        self.device_name_input.setPlaceholderText("botyaraPAD")
        self.device_name_input.setMaxLength(50)
        mic_form.addRow("Имя устройства:", self.device_name_input)

        # Выбор реального микрофона
        source_layout = QHBoxLayout()
        self.source_combo = QComboBox()
        self.source_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        source_layout.addWidget(self.source_combo)

        self.refresh_sources_btn = QPushButton("🔄")
        self.refresh_sources_btn.setFixedWidth(40)
        self.refresh_sources_btn.setToolTip("Обновить список микрофонов")
        self.refresh_sources_btn.clicked.connect(self._refresh_sources)
        source_layout.addWidget(self.refresh_sources_btn)

        mic_form.addRow("Реальный микрофон:", source_layout)

        self.pass_through_check = QCheckBox("Прокидывать реальный микрофон в виртуальный")
        self.pass_through_check.setToolTip(
            "Если включено, ваш голос из реального микрофона\n"
            "будет слышен через виртуальный микрофон\n"
            "(вместе со звуками)"
        )
        mic_form.addRow(self.pass_through_check)

        layout.addWidget(mic_group)

        # ── Группа: Воспроизведение ──
        play_group = QGroupBox("🔊 Воспроизведение")
        play_form = QFormLayout(play_group)
        play_form.setSpacing(8)

        self.default_mode_combo = QComboBox()
        self.default_mode_combo.addItem("🔊🎤 Динамик + Микрофон", "both")
        self.default_mode_combo.addItem("🔊 Только динамик", "speaker")
        self.default_mode_combo.addItem("🎤 Только микрофон", "mic")
        play_form.addRow("Режим по умолчанию:", self.default_mode_combo)

        self.overlap_check = QCheckBox("Разрешить одновременное воспроизведение нескольких звуков")
        self.overlap_check.setToolTip(
            "Если выключено, новый звук будет останавливать предыдущий"
        )
        play_form.addRow(self.overlap_check)

        layout.addWidget(play_group)

        # ── Группа: Интерфейс ──
        ui_group = QGroupBox("🎨 Интерфейс")
        ui_form = QFormLayout(ui_group)
        ui_form.setSpacing(8)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("🌙 Тёмная", "dark")
        self.theme_combo.addItem("☀️ Светлая", "light")
        ui_form.addRow("Тема:", self.theme_combo)

        layout.addWidget(ui_group)

        # ── Группа: Информация ──
        info_group = QGroupBox("ℹ️ Информация")
        info_layout = QVBoxLayout(info_group)

        info_text = QLabel(
            "botyaraPAD — звуковая панель для Linux (PipeWire)\n"
            "Использует: PyQt5, pygame, ffmpeg, PipeWire/PulseAudio\n\n"
            "Звуки воспроизводятся через виртуальный микрофон,\n"
            "который можно выбрать в Discord, OBS и других приложениях."
        )
        info_text.setStyleSheet("font-size: 12px;")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)

        layout.addWidget(info_group)

        # ── Кнопки ──
        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        buttons_layout.addStretch()

        self.apply_btn = QPushButton("✅ Применить")
        self.apply_btn.setFixedHeight(36)
        self.apply_btn.setFixedWidth(140)
        self.apply_btn.clicked.connect(self._apply_settings)
        buttons_layout.addWidget(self.apply_btn)

        self.cancel_btn = QPushButton("❌ Отмена")
        self.cancel_btn.setFixedHeight(36)
        self.cancel_btn.setFixedWidth(140)
        self.cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_btn)

        layout.addLayout(buttons_layout)

    def _load_current_settings(self):
        """Загрузить текущие настройки в UI."""
        # Имя устройства
        self.device_name_input.setText(self.config.get("device_name", "botyaraPAD"))

        # Прокидывание микрофона
        self.pass_through_check.setChecked(self.config.get("pass_through_mic", True))

        # Режим по умолчанию
        default_mode = self.config.get("default_play_mode", "both")
        index = self.default_mode_combo.findData(default_mode)
        if index >= 0:
            self.default_mode_combo.setCurrentIndex(index)

        # Overlap
        self.overlap_check.setChecked(self.config.get("allow_overlap", True))

        # Тема
        theme = self.config.get("theme", "dark")
        theme_index = self.theme_combo.findData(theme)
        if theme_index >= 0:
            self.theme_combo.setCurrentIndex(theme_index)

        # Загружаем микрофоны
        self._refresh_sources()

        # Выбираем сохранённый микрофон
        saved_source = self.config.get("source_mic", "")
        if saved_source:
            idx = self.source_combo.findData(saved_source)
            if idx >= 0:
                self.source_combo.setCurrentIndex(idx)

    def _refresh_sources(self):
        """Обновить список доступных микрофонов."""
        self.source_combo.clear()
        self.source_combo.addItem("(не выбрано)", "")

        sources = PipeWireVirtualMic.get_available_sources()
        self._sources_cache = sources

        for src in sources:
            name = src.get("name", "")
            desc = src.get("description", name)
            # Не показываем наш собственный виртуальный микрофон
            device_name = self.config.get("device_name", "botyaraPAD")
            if device_name.lower() in desc.lower():
                continue
            self.source_combo.addItem(f"🎤 {desc}", name)

    def _apply_settings(self):
        """Применить настройки."""
        old_theme = self.config.get("theme", "dark")

        new_settings = {
            "device_name": self.device_name_input.text().strip() or "botyaraPAD",
            "source_mic": self.source_combo.currentData() or "",
            "pass_through_mic": self.pass_through_check.isChecked(),
            "default_play_mode": self.default_mode_combo.currentData(),
            "allow_overlap": self.overlap_check.isChecked(),
            "theme": self.theme_combo.currentData(),
        }

        self.config.update_settings(new_settings)

        # Если тема изменилась — уведомляем
        new_theme = new_settings["theme"]
        if new_theme != old_theme:
            self.theme_changed.emit(new_theme)

        self.settings_applied.emit()

        # Предупреждаем о необходимости перезапуска виртуального микрофона
        old_device = self.config.get("device_name", "botyaraPAD")
        new_device = new_settings["device_name"]
        if old_device != new_device:
            QMessageBox.information(
                self,
                "Перезапуск",
                "Имя виртуального устройства изменено.\n"
                "Виртуальный микрофон будет пересоздан."
            )

        self.accept()

    def showEvent(self, event):
        """При показе окна — обновляем данные."""
        super().showEvent(event)
        self._load_current_settings()

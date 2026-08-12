"""
botyaraPAD - Main Window
Главное окно приложения.
"""

import os
import threading

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QListWidgetItem, QMenu, QAction,
    QFileDialog, QInputDialog, QMessageBox, QApplication,
    QLineEdit, QLabel, QPushButton, QShortcut
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QTimer, QObject
from PyQt5.QtGui import QIcon, QKeySequence

from config_manager import ConfigManager
from sound_manager import SoundLibrary, SoundInfo, SUPPORTED_FORMATS, is_supported_format
from audio_engine import AudioEngine
from ui_widgets import (
    SoundListWidget, SoundItemWidget, TopBarWidget,
    SoundEditDialog, get_theme_stylesheet
)
from ui_settings import SettingsWindow


class SignalBridge(QObject):
    """Мост для сигналов из фоновых потоков в GUI."""
    duration_loaded = pyqtSignal(int, int)  # tab_index, sound_index
    sound_finished = pyqtSignal(int)         # channel_id
    status_update = pyqtSignal(str)
    keybind_triggered = pyqtSignal(int, int) # tab_index, sound_index


class MainWindow(QMainWindow):
    """Главное окно botyaraPAD."""

    def __init__(self, config: ConfigManager, sound_library: SoundLibrary,
                 audio_engine: AudioEngine):
        super().__init__()
        self.config = config
        self.library = sound_library
        self.engine = audio_engine

        # Мост сигналов для потоков
        self.signals = SignalBridge()
        self.signals.duration_loaded.connect(self._on_duration_loaded)
        self.signals.sound_finished.connect(self._on_sound_finished)
        self.signals.status_update.connect(self._on_status_update)
        self.signals.keybind_triggered.connect(self._on_keybind_play)

        # Маппинг channel_id -> (tab_index, sound_index)
        self._playing_channels: dict[int, tuple[int, int]] = {}
        self._playing_lock = threading.Lock()

        # Результаты поиска
        self._search_results = []
        self._is_searching = False

        # Выделенные элементы
        self._selected_sounds: list[tuple[int, int]] = []  # [(tab_idx, sound_idx), ...]

        self._setup_window()
        self._setup_ui()
        self._apply_theme()
        self._setup_callbacks()
        self._start_engine()
        self._load_all_tabs()
        self._start_keybinds()

    def _setup_window(self):
        """Настройка окна."""
        self.setWindowTitle("botyaraPAD")
        width = self.config.get("window_width", 900)
        height = self.config.get("window_height", 600)
        self.resize(width, height)
        self.setMinimumSize(700, 500)

    def _setup_ui(self):
        """Создание интерфейса."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Верхняя панель ──
        self.top_bar = TopBarWidget(
            initial_volume=self.config.get("master_volume", 75),
            loop_enabled=self.config.get("loop_enabled", False)
        )
        self.top_bar.volume_changed.connect(self._on_master_volume_changed)
        self.top_bar.search_changed.connect(self._on_search_changed)
        self.top_bar.stop_all_clicked.connect(self._on_stop_all)
        self.top_bar.loop_toggled.connect(self._on_loop_toggled)
        self.top_bar.settings_clicked.connect(self._open_settings)
        self.top_bar.add_sound_clicked.connect(self._on_add_sound)
        main_layout.addWidget(self.top_bar)

        # ── Вкладки со звуками ──
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(False)  # Закрытие через контекстное меню
        self.tab_widget.setMovable(True)
        self.tab_widget.tabBarDoubleClicked.connect(self._on_tab_double_clicked)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.tab_widget.tabBar().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tab_widget.tabBar().customContextMenuRequested.connect(self._on_tab_context_menu)

        # ── Угловая панель вкладок (счётчик + кнопка "Новая вкладка") ──
        tab_corner_widget = QWidget()
        tab_corner_layout = QHBoxLayout(tab_corner_widget)
        tab_corner_layout.setContentsMargins(4, 2, 8, 2)
        tab_corner_layout.setSpacing(10)

        # Количество играющих
        self.playing_count_label = QLabel("")
        self.playing_count_label.setObjectName("statusLabel")
        tab_corner_layout.addWidget(self.playing_count_label)

        # Кнопка добавить вкладку
        self.add_tab_btn = QPushButton("➕ Вкладка")
        self.add_tab_btn.setFixedHeight(26)
        self.add_tab_btn.setCursor(Qt.PointingHandCursor)
        self.add_tab_btn.setToolTip("Добавить новую вкладку")
        self.add_tab_btn.clicked.connect(self._on_add_tab)
        tab_corner_layout.addWidget(self.add_tab_btn)

        self.tab_widget.setCornerWidget(tab_corner_widget, Qt.TopRightCorner)
        main_layout.addWidget(self.tab_widget, stretch=1)

        # ── Словарь: tab_index -> SoundListWidget ──
        self.sound_lists: dict[int, SoundListWidget] = {}

        # Таймер обновления количества играющих и прогрессбаров
        self.playing_timer = QTimer()
        self.playing_timer.timeout.connect(self._update_playing_count)
        self.playing_timer.start(100)

        # Горячие клавиши приложения
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        """Настройка горячих клавиш приложения."""
        # Ctrl+F - фокус на поиске
        self.search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.search_shortcut.activated.connect(self._focus_search)

    def _focus_search(self):
        """Фокусировка на поле поиска."""
        self.top_bar.search_input.setFocus()
        self.top_bar.search_input.selectAll()

    def _apply_theme(self):
        """Применить текущую тему."""
        theme = self.config.get("theme", "dark")
        stylesheet = get_theme_stylesheet(theme)
        self.setStyleSheet(stylesheet)

    def _setup_callbacks(self):
        """Настроить callbacks от аудио-движка."""
        self.engine.player.on_sound_finished = self._thread_safe_sound_finished

    def _thread_safe_sound_finished(self, channel_id: int):
        """Callback из фонового потока — отправляем сигнал в GUI."""
        self.signals.sound_finished.emit(channel_id)

    # ═══ Запуск движка и биндов ═════════════════════════════════

    def _start_engine(self):
        """Запустить аудио-движок в фоне."""
        def _start():
            success = self.engine.start()
            if success:
                self.signals.status_update.emit("✅ Активен")
            else:
                self.signals.status_update.emit("❌ Ошибка запуска")

        thread = threading.Thread(target=_start, daemon=True)
        thread.start()

    def _start_keybinds(self):
        """Запустить систему биндингов."""
        def play_callback(tab_idx: int, sound_idx: int):
            # Вызываем через сигнал чтобы быть в GUI потоке
            self.signals.keybind_triggered.emit(tab_idx, sound_idx)

        self.library.start_keybinds(play_callback)

    def _on_keybind_play(self, tab_index: int, sound_index: int):
        """Воспроизведение по биндингу."""
        self._on_sound_play(tab_index, sound_index, "default")

    # ═══ Загрузка вкладок ════════════════════════════════════════

    def _load_all_tabs(self):
        """Загрузить все вкладки из библиотеки."""
        # Очищаем
        while self.tab_widget.count() > 0:
            self.tab_widget.removeTab(0)
        self.sound_lists.clear()

        # Создаём вкладки
        for tab_idx in range(self.library.get_tab_count()):
            self._create_tab_ui(tab_idx)

        # Загружаем звуки для текущей вкладки
        if self.tab_widget.count() > 0:
            self._refresh_sound_list(0)

    def _create_tab_ui(self, tab_index: int):
        """Создать UI вкладки."""
        tab_name = self.library.get_tab_name(tab_index)

        # Создаём SoundListWidget
        sound_list = SoundListWidget()
        sound_list.files_dropped.connect(lambda files, idx=tab_index: self._on_files_dropped(idx, files))
        sound_list.sound_play_requested.connect(
            lambda si, mode, idx=tab_index: self._on_sound_play(idx, si, mode)
        )
        sound_list.sound_pause_requested.connect(
            lambda si, idx=tab_index: self._on_sound_pause(idx, si)
        )
        sound_list.sound_stop_requested.connect(
            lambda si, idx=tab_index: self._on_sound_stop(idx, si)
        )
        sound_list.sound_context_menu.connect(
            lambda si, pos, idx=tab_index: self._on_sound_context_menu(idx, si, pos)
        )
        sound_list.sounds_reordered.connect(
            lambda from_i, to_i, idx=tab_index: self._on_sounds_reordered(idx, from_i, to_i)
        )
        sound_list.selection_changed.connect(
            lambda indices, idx=tab_index: self._on_selection_changed(idx, indices)
        )

        self.sound_lists[tab_index] = sound_list
        self.tab_widget.addTab(sound_list, tab_name)

    def _refresh_sound_list(self, tab_index: int):
        """Обновить список звуков во вкладке."""
        if tab_index not in self.sound_lists:
            return

        sound_list = self.sound_lists[tab_index]
        sound_list.clear()

        sounds = self.library.get_sounds(tab_index)

        for i, sound in enumerate(sounds):
            item = QListWidgetItem()
            widget = SoundItemWidget(sound, i)
            widget.play_requested.connect(
                lambda si, mode, ti=tab_index: self._on_sound_play(ti, si, mode)
            )
            widget.pause_requested.connect(
                lambda si, ti=tab_index: self._on_sound_pause(ti, si)
            )
            widget.stop_requested.connect(
                lambda si, ti=tab_index: self._on_sound_stop(ti, si)
            )

            # Высота зависит от наличия кастомного имени и биндинга
            base_height = 58
            if sound.custom_name:
                base_height += 14
            if sound.keybind:
                base_height += 4

            item.setSizeHint(QSize(0, base_height))
            sound_list.addItem(item)
            sound_list.setItemWidget(item, widget)

        # Асинхронно подгружаем длительности
        self.library.preload_durations_async(
            tab_index,
            callback=lambda si, ti=tab_index: self.signals.duration_loaded.emit(ti, si)
        )

    def _refresh_all_tabs_ui(self):
        """Полностью пересоздать все вкладки."""
        self._load_all_tabs()

    def _rebuild_tab_indices(self):
        """
        Пересоздать маппинг индексов вкладок.
        Нужно после добавления/удаления вкладок.
        """
        old_lists = self.sound_lists.copy()
        self.sound_lists.clear()

        # Удаляем все вкладки из виджета
        while self.tab_widget.count() > 0:
            self.tab_widget.removeTab(0)

        # Пересоздаём
        for tab_idx in range(self.library.get_tab_count()):
            self._create_tab_ui(tab_idx)
            self._refresh_sound_list(tab_idx)

    # ═══ Обработчики вкладок ═════════════════════════════════════

    def _on_add_tab(self):
        """Добавить новую вкладку."""
        name, ok = QInputDialog.getText(
            self, "Новая вкладка", "Название вкладки:",
            QLineEdit.Normal, ""
        )
        if ok and name.strip():
            self.library.add_tab(name.strip())
            self._rebuild_tab_indices()
            # Переключаемся на новую вкладку
            self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)

    def _on_tab_double_clicked(self, index: int):
        """Двойной клик по вкладке — переименование."""
        if index < 0:
            return

        current_name = self.library.get_tab_name(index)
        name, ok = QInputDialog.getText(
            self, "Переименовать вкладку",
            "Новое название:",
            QLineEdit.Normal, current_name
        )
        if ok and name.strip():
            self.library.rename_tab(index, name.strip())
            self.tab_widget.setTabText(index, name.strip())

    def _on_tab_context_menu(self, pos):
        """Контекстное меню на вкладке."""
        index = self.tab_widget.tabBar().tabAt(pos)
        if index < 0:
            return

        menu = QMenu(self)

        rename_action = menu.addAction("✏️ Переименовать")
        rename_action.triggered.connect(lambda: self._on_tab_double_clicked(index))

        if self.library.get_tab_count() > 1:
            delete_action = menu.addAction("🗑️ Удалить")
            delete_action.triggered.connect(lambda: self._on_delete_tab(index))

        menu.exec_(self.tab_widget.tabBar().mapToGlobal(pos))

    def _on_delete_tab(self, index: int):
        """Удалить вкладку."""
        tab_name = self.library.get_tab_name(index)
        sounds_count = len(self.library.get_sounds(index))

        msg = f"Удалить вкладку \"{tab_name}\"?"
        if sounds_count > 0:
            msg += f"\nВ ней {sounds_count} звук(ов), они будут удалены."

        reply = QMessageBox.question(
            self, "Удаление вкладки", msg,
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.library.remove_tab(index)
            self._rebuild_tab_indices()

    def _on_tab_changed(self, index: int):
        """Переключение между вкладками."""
        if index >= 0 and index in self.sound_lists:
            # Если звуки ещё не загружены — загружаем
            sound_list = self.sound_lists[index]
            if sound_list.count() == 0:
                sounds = self.library.get_sounds(index)
                if sounds:
                    self._refresh_sound_list(index)

    # ═══ Обработчики звуков ══════════════════════════════════════

    def _on_add_sound(self):
        """Добавить звук через диалог выбора файла."""
        current_tab = self.tab_widget.currentIndex()
        if current_tab < 0:
            return

        # Формируем фильтр форматов
        extensions = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_FORMATS))
        file_filter = f"Аудиофайлы ({extensions});;Все файлы (*.*)"

        files, _ = QFileDialog.getOpenFileNames(
            self, "Добавить звуки", "", file_filter
        )

        if files:
            self._add_files_to_tab(current_tab, files)

    def _on_files_dropped(self, tab_index: int, files: list):
        """Обработка Drag & Drop файлов."""
        self._add_files_to_tab(tab_index, files)

    def _add_files_to_tab(self, tab_index: int, files: list):
        """Добавить файлы во вкладку."""
        added = 0
        for filepath in files:
            if is_supported_format(filepath) and os.path.exists(filepath):
                sound = self.library.add_sound(tab_index, filepath)
                if sound is not None:
                    added += 1

        if added > 0:
            self._refresh_sound_list(tab_index)
            self.top_bar.set_status(f"✅ Добавлено {added} звук(ов)")
        else:
            self.top_bar.set_status("⚠️ Не удалось добавить звуки")

    def _on_sounds_reordered(self, tab_index: int, from_index: int, to_index: int):
        """Обработка перестановки звуков."""
        self.library.move_sound(tab_index, from_index, to_index)
        self._refresh_sound_list(tab_index)
        self.top_bar.set_status("✅ Звук перемещён")

    def _on_selection_changed(self, tab_index: int, indices: list):
        """Изменение выделения звуков."""
        self._selected_sounds = [(tab_index, idx) for idx in indices]

    def _on_sound_play(self, tab_index: int, sound_index: int, play_mode: str):
        """Запрос воспроизведения звука."""
        # Если мы в режиме поиска — используем реальные индексы
        if self._is_searching and self._search_results:
            if 0 <= sound_index < len(self._search_results):
                real_tab, real_sound, _ = self._search_results[sound_index]
                tab_index = real_tab
                sound_index = real_sound

        sounds = self.library.get_sounds(tab_index)
        if not (0 <= sound_index < len(sounds)):
            return

        sound = sounds[sound_index]
        if not sound.exists:
            QMessageBox.warning(self, "Ошибка", f"Файл не найден:\n{sound.path}")
            return

        # Проверяем, не играет ли уже этот звук (тогда останавливаем)
        with self._playing_lock:
            for ch_id, (ti, si) in list(self._playing_channels.items()):
                if ti == tab_index and si == sound_index:
                    self.engine.stop_sound(ch_id)
                    self._playing_channels.pop(ch_id, None)
                    self._update_sound_widget_playing(tab_index, sound_index, False)
                    return

        # Определяем режим воспроизведения
        if play_mode == "default":
            play_mode = sound.play_mode or self.config.get("default_play_mode", "both")

        # Получаем WAV путь
        def _play_thread():
            wav_path = sound.get_wav_path()
            if wav_path is None:
                self.signals.status_update.emit(f"❌ Не удалось подготовить: {sound.display_name}")
                return

            volume = sound.volume / 100.0
            loop = self.config.get("loop_enabled", False)

            channel_id = self.engine.play_sound(
                wav_path=wav_path,
                volume=volume,
                play_mode=play_mode,
                loop=loop
            )

            if channel_id >= 0:
                with self._playing_lock:
                    self._playing_channels[channel_id] = (tab_index, sound_index)
                # Обновляем UI из GUI потока
                QTimer.singleShot(0, lambda: self._update_sound_widget_playing(
                    tab_index, sound_index, True
                ))
                self.signals.status_update.emit(f"▶ {sound.display_name}")
            else:
                self.signals.status_update.emit(f"❌ Ошибка воспроизведения: {sound.display_name}")

        thread = threading.Thread(target=_play_thread, daemon=True)
        thread.start()

    def _on_sound_pause(self, tab_index: int, sound_index: int):
        """Пауза / снятие с паузы звука."""
        if self._is_searching and self._search_results:
            if 0 <= sound_index < len(self._search_results):
                tab_index, sound_index, _ = self._search_results[sound_index]

        with self._playing_lock:
            for ch_id, (ti, si) in list(self._playing_channels.items()):
                if ti == tab_index and si == sound_index:
                    self.engine.toggle_pause(ch_id)
                    return

    def _on_sound_stop(self, tab_index: int, sound_index: int):
        """Остановить конкретный звук."""
        if self._is_searching and self._search_results:
            if 0 <= sound_index < len(self._search_results):
                tab_index, sound_index, _ = self._search_results[sound_index]

        with self._playing_lock:
            to_remove = [ch_id for ch_id, (ti, si) in self._playing_channels.items() if ti == tab_index and si == sound_index]
            for ch_id in to_remove:
                self.engine.stop_sound(ch_id)
                self._playing_channels.pop(ch_id, None)

        self._update_sound_widget_playing(tab_index, sound_index, False)

    def _on_sound_context_menu(self, tab_index: int, sound_index: int, pos):
        """Контекстное меню звука."""
        menu = QMenu(self)

        if sound_index < 0:
            # Клик по пустому месту
            add_action = menu.addAction("➕ Добавить звуки")
            add_action.triggered.connect(self._on_add_sound)
            menu.exec_(pos)
            return

        # Если поиск — пересчитываем индексы
        real_tab = tab_index
        real_sound = sound_index
        if self._is_searching and self._search_results:
            if 0 <= sound_index < len(self._search_results):
                real_tab, real_sound, _ = self._search_results[sound_index]

        sounds = self.library.get_sounds(real_tab)
        if not (0 <= real_sound < len(sounds)):
            return

        sound = sounds[real_sound]

        # Проверяем множественное выделение
        selected_count = len(self._selected_sounds)
        is_multi = selected_count > 1

        if is_multi:
            # Меню для множественного выделения
            self._show_multi_selection_menu(menu, pos)
            return

        # ── Режимы воспроизведения ──
        play_both = menu.addAction("🔊🎤 Динамик + Микрофон")
        play_both.triggered.connect(
            lambda: self._on_sound_play(real_tab, real_sound, "both")
        )

        play_speaker = menu.addAction("🔊 Только динамик")
        play_speaker.triggered.connect(
            lambda: self._on_sound_play(real_tab, real_sound, "speaker")
        )

        play_mic = menu.addAction("🎤 Только микрофон")
        play_mic.triggered.connect(
            lambda: self._on_sound_play(real_tab, real_sound, "mic")
        )

        menu.addSeparator()

        # ── Настройки звука ──
        set_name = menu.addAction("✏️ Кастомное название")
        set_name.triggered.connect(
            lambda: self._edit_sound_name(real_tab, real_sound)
        )

        set_volume = menu.addAction("🔊 Громкость")
        set_volume.triggered.connect(
            lambda: self._edit_sound_volume(real_tab, real_sound)
        )

        set_mode = menu.addAction("🎛️ Режим по умолчанию")
        set_mode.triggered.connect(
            lambda: self._edit_sound_mode(real_tab, real_sound)
        )

        set_keybind = menu.addAction("⌨️ Горячая клавиша")
        set_keybind.triggered.connect(
            lambda: self._edit_sound_keybind(real_tab, real_sound)
        )

        menu.addSeparator()

        # ── Перемещение между вкладками ──
        if self.library.get_tab_count() > 1:
            move_menu = menu.addMenu("📁 Переместить в...")
            for i in range(self.library.get_tab_count()):
                if i != real_tab:
                    tab_name = self.library.get_tab_name(i)
                    move_action = move_menu.addAction(tab_name)
                    move_action.triggered.connect(
                        lambda checked, from_t=real_tab, si=real_sound, to_t=i:
                        self._move_sound_to_tab(from_t, si, to_t)
                    )

        menu.addSeparator()

        # ── Удаление ──
        delete_action = menu.addAction("🗑️ Удалить")
        delete_action.triggered.connect(
            lambda: self._delete_sound(real_tab, real_sound)
        )

        menu.exec_(pos)

    def _show_multi_selection_menu(self, menu: QMenu, pos):
        """Контекстное меню для множественного выделения."""
        selected_count = len(self._selected_sounds)

        info_action = menu.addAction(f"Выбрано: {selected_count} звук(ов)")
        info_action.setEnabled(False)

        menu.addSeparator()

        # Удалить выбранные
        delete_action = menu.addAction("🗑️ Удалить выбранные")
        delete_action.triggered.connect(self._delete_selected_sounds)

        # Переместить в другую вкладку
        if self.library.get_tab_count() > 1:
            # Проверяем что все звуки из одной вкладки
            tabs = set(tab_idx for tab_idx, _ in self._selected_sounds)
            if len(tabs) == 1:
                current_tab = list(tabs)[0]
                move_menu = menu.addMenu("📁 Переместить в...")
                for i in range(self.library.get_tab_count()):
                    if i != current_tab:
                        tab_name = self.library.get_tab_name(i)
                        move_action = move_menu.addAction(tab_name)
                        move_action.triggered.connect(
                            lambda checked, to_t=i: self._move_selected_to_tab(to_t)
                        )

        menu.exec_(pos)

    def _delete_selected_sounds(self):
        """Удалить выбранные звуки."""
        if not self._selected_sounds:
            return

        count = len(self._selected_sounds)
        reply = QMessageBox.question(
            self, "Удаление звуков",
            f"Удалить {count} выбранных звук(ов)?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Сортируем по убыванию индексов чтобы не сбивались при удалении
            sorted_sounds = sorted(self._selected_sounds, key=lambda x: (x[0], x[1]), reverse=True)

            for tab_idx, sound_idx in sorted_sounds:
                self.library.remove_sound(tab_idx, sound_idx)

            # Обновляем только затронутые вкладки
            affected_tabs = set(tab_idx for tab_idx, _ in sorted_sounds)
            for tab_idx in affected_tabs:
                self._refresh_sound_list(tab_idx)

            self._selected_sounds.clear()
            self.top_bar.set_status(f"✅ Удалено {count} звук(ов)")

    def _move_selected_to_tab(self, to_tab: int):
        """Переместить выбранные звуки в другую вкладку."""
        if not self._selected_sounds:
            return

        # Проверяем что все из одной вкладки
        tabs = set(tab_idx for tab_idx, _ in self._selected_sounds)
        if len(tabs) != 1:
            return

        from_tab = list(tabs)[0]

        # Сортируем по убыванию индексов
        sorted_sounds = sorted(self._selected_sounds, key=lambda x: x[1], reverse=True)

        for _, sound_idx in sorted_sounds:
            self.library.move_sound_to_tab(from_tab, sound_idx, to_tab)

        self._refresh_sound_list(from_tab)
        self._refresh_sound_list(to_tab)

        self._selected_sounds.clear()
        self.top_bar.set_status(f"✅ Перемещено {len(sorted_sounds)} звук(ов)")

    # ═══ Редактирование звуков ════════════════════════════════════

    def _edit_sound_name(self, tab_index: int, sound_index: int):
        """Редактирование кастомного названия звука."""
        sounds = self.library.get_sounds(tab_index)
        if not (0 <= sound_index < len(sounds)):
            return

        sound = sounds[sound_index]
        new_name = SoundEditDialog.edit_custom_name(self, sound.custom_name)
        if new_name != sound.custom_name:
            self.library.update_sound(tab_index, sound_index, custom_name=new_name)
            self._refresh_sound_list(tab_index)

    def _edit_sound_volume(self, tab_index: int, sound_index: int):
        """Редактирование громкости звука."""
        sounds = self.library.get_sounds(tab_index)
        if not (0 <= sound_index < len(sounds)):
            return

        sound = sounds[sound_index]
        new_vol = SoundEditDialog.edit_volume(self, sound.volume)
        if new_vol != sound.volume:
            self.library.update_sound(tab_index, sound_index, volume=new_vol)
            self._refresh_sound_list(tab_index)

    def _edit_sound_mode(self, tab_index: int, sound_index: int):
        """Редактирование режима воспроизведения звука."""
        sounds = self.library.get_sounds(tab_index)
        if not (0 <= sound_index < len(sounds)):
            return

        mode = SoundEditDialog.choose_play_mode(self)
        if mode:
            self.library.update_sound(tab_index, sound_index, play_mode=mode)
            self._refresh_sound_list(tab_index)

    def _edit_sound_keybind(self, tab_index: int, sound_index: int):
        """Редактирование биндинга звука."""
        sounds = self.library.get_sounds(tab_index)
        if not (0 <= sound_index < len(sounds)):
            return

        sound = sounds[sound_index]
        new_keybind = SoundEditDialog.edit_keybind(self, sound.keybind)

        if new_keybind != sound.keybind:
            # Проверяем что такой биндинг не занят
            if new_keybind:
                conflict = self._check_keybind_conflict(tab_index, sound_index, new_keybind)
                if conflict:
                    tab_name, sound_name = conflict
                    reply = QMessageBox.question(
                        self,
                        "Конфликт биндинга",
                        f"Биндинг '{new_keybind}' уже используется:\n"
                        f"Вкладка: {tab_name}\n"
                        f"Звук: {sound_name}\n\n"
                        f"Заменить?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        return
                    # Удаляем старый биндинг
                    self._remove_conflicting_keybind(new_keybind)

            self.library.update_sound(tab_index, sound_index, keybind=new_keybind)
            self._refresh_sound_list(tab_index)

            if new_keybind:
                self.top_bar.set_status(f"✅ Установлен биндинг: {new_keybind}")
            else:
                self.top_bar.set_status("✅ Биндинг удалён")

    def _check_keybind_conflict(self, exclude_tab: int, exclude_sound: int,
                                 keybind: str) -> tuple[str, str] | None:
        """
        Проверить конфликт биндинга.
        Возвращает (tab_name, sound_name) если найден конфликт, иначе None.
        """
        for tab_idx in range(self.library.get_tab_count()):
            sounds = self.library.get_sounds(tab_idx)
            for sound_idx, sound in enumerate(sounds):
                if tab_idx == exclude_tab and sound_idx == exclude_sound:
                    continue
                if sound.keybind == keybind:
                    tab_name = self.library.get_tab_name(tab_idx)
                    return (tab_name, sound.display_name)
        return None

    def _remove_conflicting_keybind(self, keybind: str):
        """Удалить конфликтующий биндинг."""
        for tab_idx in range(self.library.get_tab_count()):
            sounds = self.library.get_sounds(tab_idx)
            for sound_idx, sound in enumerate(sounds):
                if sound.keybind == keybind:
                    self.library.update_sound(tab_idx, sound_idx, keybind="")
                    return

    def _move_sound_to_tab(self, from_tab: int, sound_index: int, to_tab: int):
        """Переместить звук в другую вкладку."""
        self.library.move_sound_to_tab(from_tab, sound_index, to_tab)
        self._refresh_sound_list(from_tab)
        self._refresh_sound_list(to_tab)
        self.top_bar.set_status("✅ Звук перемещён")

    def _delete_sound(self, tab_index: int, sound_index: int):
        """Удалить звук."""
        sounds = self.library.get_sounds(tab_index)
        if not (0 <= sound_index < len(sounds)):
            return

        sound = sounds[sound_index]
        reply = QMessageBox.question(
            self, "Удаление звука",
            f"Удалить \"{sound.display_name}\" из списка?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.library.remove_sound(tab_index, sound_index)
            self._refresh_sound_list(tab_index)

    # ═══ Поиск ═══════════════════════════════════════════════════

    def _on_search_changed(self, query: str):
        """Обработка поиска."""
        query = query.strip()

        if not query:
            # Сбрасываем поиск — показываем текущую вкладку
            self._is_searching = False
            self._search_results = []
            current = self.tab_widget.currentIndex()
            if current >= 0:
                self._refresh_sound_list(current)
            return

        # Ищем
        self._is_searching = True
        self._search_results = self.library.search_sounds(query)

        # Показываем результаты в текущем списке
        current = self.tab_widget.currentIndex()
        if current < 0:
            return

        sound_list = self.sound_lists.get(current)
        if sound_list is None:
            return

        sound_list.clear()

        if not self._search_results:
            # Нет результатов
            item = QListWidgetItem("🔍 Ничего не найдено")
            item.setFlags(Qt.NoItemFlags)
            sound_list.addItem(item)
            return

        for i, (tab_idx, sound_idx, sound) in enumerate(self._search_results):
            tab_name = self.library.get_tab_name(tab_idx)
            item = QListWidgetItem()
            widget = SoundItemWidget(sound, i)
            widget.play_requested.connect(
                lambda idx, mode: self._on_sound_play(0, idx, mode)
            )
            widget.pause_requested.connect(
                lambda idx: self._on_sound_pause(0, idx)
            )
            widget.stop_requested.connect(
                lambda idx: self._on_sound_stop(0, idx)
            )

            # Добавляем метку вкладки в filename_label
            if widget.filename_label is None:
                # Создаём новый label для вкладки
                main_layout = widget.layout()
                info_layout = main_layout.itemAt(1).layout()

                tab_label = QLabel(f"📁 {tab_name}")
                tab_label.setStyleSheet("color: #6c7086; font-size: 11px;")
                info_layout.addWidget(tab_label)
                widget.filename_label = tab_label
            else:
                # Обновляем существующий
                original_text = widget.filename_label.text()
                widget.filename_label.setText(f"📁 {tab_name} • {original_text}")

            # Высота
            base_height = 64
            if sound.custom_name:
                base_height += 14
            if sound.keybind:
                base_height += 4

            item.setSizeHint(QSize(0, base_height))
            sound_list.addItem(item)
            sound_list.setItemWidget(item, widget)

        self.top_bar.set_status(f"🔍 Найдено: {len(self._search_results)}")

    # ═══ Управление воспроизведением ═════════════════════════════

    def _on_master_volume_changed(self, value: int):
        """Изменение мастер-громкости."""
        self.engine.set_master_volume(value)

    def _on_stop_all(self):
        """Остановить все звуки."""
        self.engine.stop_all_sounds()
        with self._playing_lock:
            self._playing_channels.clear()
        # Обновляем UI
        self._reset_all_playing_indicators()
        self.top_bar.set_status("⏹ Остановлено")

    def _on_loop_toggled(self, enabled: bool):
        """Переключение зацикливания."""
        self.config.set("loop_enabled", enabled)

    def _on_sound_finished(self, channel_id: int):
        """Звук закончил воспроизведение."""
        with self._playing_lock:
            location = self._playing_channels.pop(channel_id, None)

        if location:
            tab_idx, sound_idx = location
            self._update_sound_widget_playing(tab_idx, sound_idx, False)

    def _update_sound_widget_playing(self, tab_index: int, sound_index: int, playing: bool):
        """Обновить индикатор воспроизведения у виджета звука."""
        if tab_index not in self.sound_lists:
            return

        sound_list = self.sound_lists[tab_index]

        # Если в режиме поиска — ищем по результатам
        if self._is_searching:
            for i, (t_idx, s_idx, _) in enumerate(self._search_results):
                if t_idx == tab_index and s_idx == sound_index:
                    if 0 <= i < sound_list.count():
                        item = sound_list.item(i)
                        widget = sound_list.itemWidget(item)
                        if isinstance(widget, SoundItemWidget):
                            widget.set_playing(playing)
            return

        # Обычный режим
        if 0 <= sound_index < sound_list.count():
            item = sound_list.item(sound_index)
            widget = sound_list.itemWidget(item)
            if isinstance(widget, SoundItemWidget):
                widget.set_playing(playing)

    def _reset_all_playing_indicators(self):
        """Сбросить все индикаторы воспроизведения."""
        for tab_idx, sound_list in self.sound_lists.items():
            for i in range(sound_list.count()):
                item = sound_list.item(i)
                widget = sound_list.itemWidget(item)
                if isinstance(widget, SoundItemWidget):
                    widget.set_playing(False)

    def _update_playing_count(self):
        """Обновить счётчик играющих звуков и динамические шкалы прогресса."""
        count = self.engine.playing_count
        if count > 0:
            self.playing_count_label.setText(f"▶ Играет: {count}")
        else:
            self.playing_count_label.setText("")

        # Получаем данные активных воспроизведений
        active_playbacks = self.engine.get_active_playbacks()

        active_sound_map = {}
        with self._playing_lock:
            for ch_id, pinfo in active_playbacks.items():
                if ch_id in self._playing_channels:
                    loc = self._playing_channels[ch_id]
                    active_sound_map[loc] = pinfo

        for tab_idx, sound_list in self.sound_lists.items():
            for row in range(sound_list.count()):
                item = sound_list.item(row)
                widget = sound_list.itemWidget(item)
                if isinstance(widget, SoundItemWidget):
                    if self._is_searching and self._search_results and row < len(self._search_results):
                        real_t, real_s, _ = self._search_results[row]
                        key = (real_t, real_s)
                    else:
                        key = (tab_idx, widget.index)

                    if key in active_sound_map:
                        pinfo = active_sound_map[key]
                        widget.set_playback_progress(
                            pinfo["elapsed"],
                            pinfo["duration"],
                            pinfo["is_paused"]
                        )
                    elif widget._is_playing:
                        widget.set_stopped()

    # ═══ Callbacks из потоков ════════════════════════════════════

    def _on_duration_loaded(self, tab_index: int, sound_index: int):
        """Длительность звука загружена — обновляем UI."""
        if tab_index not in self.sound_lists:
            return

        sound_list = self.sound_lists[tab_index]
        if 0 <= sound_index < sound_list.count():
            item = sound_list.item(sound_index)
            widget = sound_list.itemWidget(item)
            if isinstance(widget, SoundItemWidget):
                widget.update_duration()

    def _on_status_update(self, text: str):
        """Обновление статуса из потока."""
        self.top_bar.set_status(text)

    # ═══ Настройки ══════════════════════════════════════════════

    def _open_settings(self):
        """Открыть окно настроек."""
        dialog = SettingsWindow(self.config, self)
        dialog.settings_applied.connect(self._on_settings_applied)
        dialog.theme_changed.connect(self._on_theme_changed)
        dialog.exec_()

    def _on_settings_applied(self):
        """Настройки применены."""
        # Обновляем мастер-громкость
        self.top_bar.set_volume(self.config.get("master_volume", 75))

        # Получаем новое устройство вывода
        new_sink = self.config.get("speaker_sink", "")

        # Перезапускаем движок для применения настроек
        def _restart():
            self.engine.stop()
            import time
            time.sleep(0.5)

            # Применяем новый sink
            if new_sink:
                self.engine.set_speaker_sink(new_sink)

            success = self.engine.start()
            if success:
                self.signals.status_update.emit("✅ Настройки применены")
            else:
                self.signals.status_update.emit("❌ Ошибка перезапуска")

        thread = threading.Thread(target=_restart, daemon=True)
        thread.start()

    def _on_theme_changed(self, theme: str):
        """Тема изменена."""
        self._apply_theme()

    # ═══ Закрытие ═══════════════════════════════════════════════

    def closeEvent(self, event):
        """Обработка закрытия окна."""
        self.config.update_settings({
            "window_width": self.width(),
            "window_height": self.height()
        })

        self.library.stop_keybinds()
        self.playing_timer.stop()
        try:
            self.engine.stop()
        except Exception:
            pass

        event.accept()

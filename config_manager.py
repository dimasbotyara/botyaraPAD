"""
botyaraPAD - Config Manager
Управление настройками приложения.
Сохранение и загрузка из settings.json и tabs.json
"""

import json
import os

# Директория проекта (где лежит этот скрипт)
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(PROJECT_DIR, "settings.json")
TABS_FILE = os.path.join(PROJECT_DIR, "tabs.json")


DEFAULT_SETTINGS = {
    "device_name": "botyaraPAD",
    "source_mic": "",
    "speaker_sink": "",  # Устройство вывода для динамика
    "pass_through_mic": True,
    "theme": "dark",
    "default_play_mode": "both",  # "both", "mic", "speaker"
    "master_volume": 75,
    "allow_overlap": True,  # несколько звуков одновременно
    "loop_enabled": False,
    "window_width": 900,
    "window_height": 600,
}

DEFAULT_TABS = {
    "tabs": [
        {
            "name": "Общее",
            "sounds": []
        }
    ]
}


class ConfigManager:
    """Менеджер конфигурации — загрузка, сохранение, доступ к настройкам."""

    def __init__(self):
        self.settings = {}
        self.tabs_data = {}
        self.load_settings()
        self.load_tabs()

    # ── Настройки ──────────────────────────────────────────────

    def load_settings(self):
        """Загрузить настройки из settings.json."""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                # Мержим с дефолтными (на случай новых полей)
                self.settings = {**DEFAULT_SETTINGS, **saved}
            except (json.JSONDecodeError, IOError) as e:
                print(f"[ConfigManager] Ошибка загрузки settings.json: {e}")
                self.settings = DEFAULT_SETTINGS.copy()
        else:
            self.settings = DEFAULT_SETTINGS.copy()
            self.save_settings()

    def save_settings(self):
        """Сохранить настройки в settings.json."""
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[ConfigManager] Ошибка сохранения settings.json: {e}")

    def get(self, key, default=None):
        """Получить значение настройки."""
        return self.settings.get(key, default)

    def set(self, key, value):
        """Установить значение настройки и сохранить."""
        self.settings[key] = value
        self.save_settings()

    def get_all_settings(self):
        """Получить копию всех настроек."""
        return self.settings.copy()

    def update_settings(self, new_settings: dict):
        """Обновить несколько настроек разом и сохранить."""
        self.settings.update(new_settings)
        self.save_settings()

    # ── Вкладки и звуки ───────────────────────────────────────

    def load_tabs(self):
        """Загрузить вкладки из tabs.json."""
        if os.path.exists(TABS_FILE):
            try:
                with open(TABS_FILE, "r", encoding="utf-8") as f:
                    self.tabs_data = json.load(f)
                # Валидация структуры
                if "tabs" not in self.tabs_data:
                    self.tabs_data = DEFAULT_TABS.copy()
            except (json.JSONDecodeError, IOError) as e:
                print(f"[ConfigManager] Ошибка загрузки tabs.json: {e}")
                self.tabs_data = DEFAULT_TABS.copy()
        else:
            self.tabs_data = DEFAULT_TABS.copy()
            self.save_tabs()

    def save_tabs(self):
        """Сохранить вкладки в tabs.json."""
        try:
            with open(TABS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.tabs_data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[ConfigManager] Ошибка сохранения tabs.json: {e}")

    def get_tabs(self) -> list:
        """Получить список вкладок."""
        return self.tabs_data.get("tabs", [])

    def add_tab(self, name: str):
        """Добавить новую вкладку."""
        self.tabs_data["tabs"].append({
            "name": name,
            "sounds": []
        })
        self.save_tabs()

    def remove_tab(self, index: int):
        """Удалить вкладку по индексу."""
        tabs = self.tabs_data.get("tabs", [])
        if 0 <= index < len(tabs):
            tabs.pop(index)
            # Если удалили все вкладки — создаём дефолтную
            if len(tabs) == 0:
                tabs.append({"name": "Общее", "sounds": []})
            self.save_tabs()

    def rename_tab(self, index: int, new_name: str):
        """Переименовать вкладку."""
        tabs = self.tabs_data.get("tabs", [])
        if 0 <= index < len(tabs):
            tabs[index]["name"] = new_name
            self.save_tabs()

    def get_sounds(self, tab_index: int) -> list:
        """Получить список звуков во вкладке."""
        tabs = self.tabs_data.get("tabs", [])
        if 0 <= tab_index < len(tabs):
            return tabs[tab_index].get("sounds", [])
        return []

    def add_sound(self, tab_index: int, sound_data: dict):
        """
        Добавить звук во вкладку.
        sound_data: {
            "path": str,
            "custom_name": str,
            "volume": int (0-100),
            "play_mode": str ("both"/"mic"/"speaker"),
            "keybind": str (опционально, например "Ctrl+1")
        }
        """
        tabs = self.tabs_data.get("tabs", [])
        if 0 <= tab_index < len(tabs):
            tabs[tab_index]["sounds"].append(sound_data)
            self.save_tabs()

    def remove_sound(self, tab_index: int, sound_index: int):
        """Удалить звук из вкладки."""
        tabs = self.tabs_data.get("tabs", [])
        if 0 <= tab_index < len(tabs):
            sounds = tabs[tab_index].get("sounds", [])
            if 0 <= sound_index < len(sounds):
                sounds.pop(sound_index)
                self.save_tabs()

    def update_sound(self, tab_index: int, sound_index: int, sound_data: dict):
        """Обновить данные звука."""
        tabs = self.tabs_data.get("tabs", [])
        if 0 <= tab_index < len(tabs):
            sounds = tabs[tab_index].get("sounds", [])
            if 0 <= sound_index < len(sounds):
                sounds[sound_index].update(sound_data)
                self.save_tabs()

    def move_sound(self, tab_index: int, from_index: int, to_index: int):
        """Переместить звук внутри вкладки."""
        tabs = self.tabs_data.get("tabs", [])
        if 0 <= tab_index < len(tabs):
            sounds = tabs[tab_index].get("sounds", [])
            if 0 <= from_index < len(sounds) and 0 <= to_index < len(sounds):
                sound = sounds.pop(from_index)
                sounds.insert(to_index, sound)
                self.save_tabs()

    def move_sound_to_tab(self, from_tab: int, sound_index: int, to_tab: int):
        """Переместить звук из одной вкладки в другую."""
        tabs = self.tabs_data.get("tabs", [])
        if (0 <= from_tab < len(tabs) and 0 <= to_tab < len(tabs)):
            sounds = tabs[from_tab].get("sounds", [])
            if 0 <= sound_index < len(sounds):
                sound = sounds.pop(sound_index)
                tabs[to_tab]["sounds"].append(sound)
                self.save_tabs()

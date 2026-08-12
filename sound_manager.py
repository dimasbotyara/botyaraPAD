"""
botyaraPAD - Sound Manager
Управление метаданными звуков: длительность, форматы, конвертация, биндинг клавиш.
"""

import os
import subprocess
import json
import threading
from typing import Optional, Tuple, Callable

from pynput import keyboard


# Поддерживаемые форматы
SUPPORTED_FORMATS = {
    ".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac",
    ".wma", ".opus", ".aiff", ".aif", ".mp2", ".ac3",
    ".amr", ".ape", ".webm", ".mka", ".spx"
}


def is_supported_format(filepath: str) -> bool:
    """Проверить, поддерживается ли формат файла."""
    _, ext = os.path.splitext(filepath)
    return ext.lower() in SUPPORTED_FORMATS


def get_audio_duration(filepath: str) -> Optional[float]:
    """
    Получить длительность аудиофайла в секундах через ffprobe.
    Возвращает None если не удалось определить.
    """
    if not os.path.exists(filepath):
        return None

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                filepath
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            duration = data.get("format", {}).get("duration")
            if duration is not None:
                return float(duration)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError, FileNotFoundError) as e:
        print(f"[SoundManager] Ошибка получения длительности {filepath}: {e}")

    return None


def format_duration(seconds: Optional[float]) -> str:
    """Отформатировать длительность в mm:ss или hh:mm:ss."""
    if seconds is None:
        return "??:??"

    seconds = int(seconds)
    if seconds < 0:
        return "0:00"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def get_file_display_name(filepath: str) -> str:
    """Получить имя файла для отображения (без пути)."""
    return os.path.basename(filepath)


def convert_to_wav_temp(filepath: str, temp_dir: str = "/tmp/botyarapad") -> Optional[str]:
    """
    Конвертировать аудиофайл во временный WAV для воспроизведения через pygame.
    Возвращает путь к временному файлу или None при ошибке.
    """
    os.makedirs(temp_dir, exist_ok=True)

    # Генерируем имя временного файла
    basename = os.path.splitext(os.path.basename(filepath))[0]
    # Добавляем хеш пути чтобы избежать коллизий
    path_hash = str(abs(hash(filepath)))[:8]
    temp_path = os.path.join(temp_dir, f"{basename}_{path_hash}.wav")

    # Если уже конвертировали — возвращаем кеш
    if os.path.exists(temp_path):
        # Проверяем что оригинал не изменился
        orig_mtime = os.path.getmtime(filepath)
        temp_mtime = os.path.getmtime(temp_path)
        if temp_mtime >= orig_mtime:
            return temp_path

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",  # перезаписать если есть
                "-i", filepath,
                "-acodec", "pcm_s16le",
                "-ar", "44100",
                "-ac", "2",
                temp_path
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return temp_path
        else:
            print(f"[SoundManager] ffmpeg ошибка: {result.stderr}")
            return None
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"[SoundManager] Ошибка конвертации {filepath}: {e}")
        return None


def cleanup_temp_files(temp_dir: str = "/tmp/botyarapad"):
    """Очистить временные файлы."""
    if os.path.exists(temp_dir):
        try:
            for f in os.listdir(temp_dir):
                fpath = os.path.join(temp_dir, f)
                if os.path.isfile(fpath):
                    os.remove(fpath)
        except OSError as e:
            print(f"[SoundManager] Ошибка очистки временных файлов: {e}")


def parse_keybind(keybind_str: str) -> Optional[set]:
    """
    Парсинг строки биндинга в набор клавиш.
    Например: "Ctrl+Shift+A" -> {Key.ctrl_l, Key.shift, KeyCode(char='a')}
    """
    if not keybind_str or keybind_str.strip() == "":
        return None

    parts = [p.strip().lower() for p in keybind_str.split('+')]
    keys = set()

    key_mapping = {
        'ctrl': keyboard.Key.ctrl_l,
        'control': keyboard.Key.ctrl_l,
        'alt': keyboard.Key.alt_l,
        'shift': keyboard.Key.shift,
        'super': keyboard.Key.cmd,
        'win': keyboard.Key.cmd,
        'meta': keyboard.Key.cmd,
    }

    for part in parts:
        if part in key_mapping:
            keys.add(key_mapping[part])
        elif len(part) == 1:
            # Обычная клавиша
            keys.add(keyboard.KeyCode.from_char(part))
        else:
            # Пытаемся как специальную клавишу
            try:
                keys.add(getattr(keyboard.Key, part))
            except AttributeError:
                print(f"[Keybind] Неизвестная клавиша: {part}")
                return None

    return keys if keys else None


def format_keybind(keys_set: Optional[set]) -> str:
    """Форматировать набор клавиш обратно в строку."""
    if not keys_set:
        return ""

    parts = []
    for key in keys_set:
        if isinstance(key, keyboard.Key):
            name = key.name
            if name in ('ctrl_l', 'ctrl_r'):
                parts.append('Ctrl')
            elif name in ('alt_l', 'alt_r'):
                parts.append('Alt')
            elif name in ('shift', 'shift_l', 'shift_r'):
                parts.append('Shift')
            elif name in ('cmd', 'cmd_l', 'cmd_r'):
                parts.append('Super')
            else:
                parts.append(name.capitalize())
        elif isinstance(key, keyboard.KeyCode):
            if key.char:
                parts.append(key.char.upper())

    return '+'.join(sorted(parts))


class SoundInfo:
    """Информация о звуковом файле."""

    def __init__(self, path: str, custom_name: str = "", volume: int = 100,
                 play_mode: str = "both", keybind: str = ""):
        self.path = path
        self.custom_name = custom_name
        self.volume = volume  # 0-100
        self.play_mode = play_mode  # "both", "mic", "speaker"
        self.keybind = keybind  # строка типа "Ctrl+Shift+A"
        self._duration: Optional[float] = None
        self._duration_loaded = False
        self._wav_cache: Optional[str] = None

    @property
    def display_name(self) -> str:
        """Имя для отображения — кастомное или имя файла."""
        if self.custom_name:
            return self.custom_name
        return get_file_display_name(self.path)

    @property
    def filename(self) -> str:
        """Оригинальное имя файла."""
        return get_file_display_name(self.path)

    @property
    def exists(self) -> bool:
        """Существует ли файл."""
        return os.path.exists(self.path)

    @property
    def duration(self) -> Optional[float]:
        """Длительность в секундах (ленивая загрузка)."""
        if not self._duration_loaded:
            self._duration = get_audio_duration(self.path)
            self._duration_loaded = True
        return self._duration

    @property
    def duration_str(self) -> str:
        """Отформатированная длительность."""
        return format_duration(self.duration)

    def get_wav_path(self) -> Optional[str]:
        """
        Получить путь к WAV-версии файла.
        Если файл уже WAV — возвращает оригинальный путь.
        Иначе конвертирует во временный WAV.
        """
        if not self.exists:
            return None

        _, ext = os.path.splitext(self.path)
        if ext.lower() == ".wav":
            return self.path

        if self._wav_cache is None or not os.path.exists(self._wav_cache):
            self._wav_cache = convert_to_wav_temp(self.path)

        return self._wav_cache

    def to_dict(self) -> dict:
        """Сериализовать в словарь для сохранения."""
        return {
            "path": self.path,
            "custom_name": self.custom_name,
            "volume": self.volume,
            "play_mode": self.play_mode,
            "keybind": self.keybind,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SoundInfo":
        """Создать из словаря."""
        return cls(
            path=data.get("path", ""),
            custom_name=data.get("custom_name", ""),
            volume=data.get("volume", 100),
            play_mode=data.get("play_mode", "both"),
            keybind=data.get("keybind", ""),
        )

    def __repr__(self):
        return f"SoundInfo('{self.display_name}', vol={self.volume}, mode={self.play_mode}, bind={self.keybind})"


class KeybindManager:
    """Менеджер горячих клавиш для звуков."""

    def __init__(self):
        self._bindings: dict[frozenset, Callable] = {}  # frozenset клавиш -> callback
        self._pressed_keys: set = set()
        self._listener: Optional[keyboard.Listener] = None
        self._lock = threading.Lock()
        self._enabled = True

    def start(self):
        """Запустить прослушивание клавиатуры."""
        if self._listener is not None:
            return

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._listener.start()
        print("[KeybindManager] Запущен")

    def stop(self):
        """Остановить прослушивание."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._bindings.clear()
        self._pressed_keys.clear()
        print("[KeybindManager] Остановлен")

    def set_enabled(self, enabled: bool):
        """Включить/выключить обработку биндов."""
        self._enabled = enabled

    def register(self, keybind_str: str, callback: Callable):
        """
        Зарегистрировать биндинг.
        keybind_str: строка типа "Ctrl+Shift+A"
        callback: функция без аргументов
        """
        keys = parse_keybind(keybind_str)
        if keys is None:
            return False

        with self._lock:
            key_frozen = frozenset(keys)
            self._bindings[key_frozen] = callback

        print(f"[KeybindManager] Зарегистрирован: {keybind_str}")
        return True

    def unregister(self, keybind_str: str):
        """Удалить биндинг."""
        keys = parse_keybind(keybind_str)
        if keys is None:
            return

        with self._lock:
            key_frozen = frozenset(keys)
            self._bindings.pop(key_frozen, None)

    def unregister_all(self):
        """Удалить все биндинги."""
        with self._lock:
            self._bindings.clear()

    def _normalize_key(self, key):
        """Нормализация клавиш (ctrl_l и ctrl_r -> ctrl_l и т.д.)."""
        if hasattr(key, 'name'):
            name = key.name
            if name in ('ctrl_r',):
                return keyboard.Key.ctrl_l
            elif name in ('alt_r',):
                return keyboard.Key.alt_l
            elif name in ('shift_r', 'shift_l'):
                return keyboard.Key.shift
            elif name in ('cmd_r', 'cmd_l'):
                return keyboard.Key.cmd
        return key

    def _on_press(self, key):
        """Обработка нажатия клавиши."""
        if not self._enabled:
            return

        key = self._normalize_key(key)
        self._pressed_keys.add(key)

        # Проверяем есть ли совпадение с зарегистрированными комбинациями
        with self._lock:
            current_combo = frozenset(self._pressed_keys)
            callback = self._bindings.get(current_combo)
            if callback:
                try:
                    callback()
                except Exception as e:
                    print(f"[KeybindManager] Ошибка в callback: {e}")

    def _on_release(self, key):
        """Обработка отпускания клавиши."""
        if not self._enabled:
            return

        key = self._normalize_key(key)
        self._pressed_keys.discard(key)


class SoundLibrary:
    """Библиотека звуков — управляет вкладками и звуками, синхронизируется с ConfigManager."""

    def __init__(self, config_manager):
        self.config = config_manager
        self.tabs: list[Tuple[str, list[SoundInfo]]] = []  # [(name, [SoundInfo, ...]), ...]
        self.keybind_manager = KeybindManager()
        self._sound_play_callback: Optional[Callable[[int, int], None]] = None
        self._load_from_config()

    def _load_from_config(self):
        """Загрузить данные из конфига."""
        self.tabs = []
        for tab_data in self.config.get_tabs():
            name = tab_data.get("name", "Без названия")
            sounds = []
            for sound_data in tab_data.get("sounds", []):
                sound = SoundInfo.from_dict(sound_data)
                sounds.append(sound)
            self.tabs.append((name, sounds))

        # Если вообще нет вкладок — создаём дефолтную
        if not self.tabs:
            self.tabs.append(("Общее", []))

    def _save_to_config(self):
        """Сохранить данные в конфиг."""
        tabs_data = {"tabs": []}
        for name, sounds in self.tabs:
            tab = {
                "name": name,
                "sounds": [s.to_dict() for s in sounds]
            }
            tabs_data["tabs"].append(tab)
        self.config.tabs_data = tabs_data
        self.config.save_tabs()

    def start_keybinds(self, play_callback: Callable[[int, int], None]):
        """
        Запустить систему биндов.
        play_callback(tab_index, sound_index) вызывается при нажатии биндинга.
        """
        self._sound_play_callback = play_callback
        self.keybind_manager.start()
        self._register_all_keybinds()

    def stop_keybinds(self):
        """Остановить систему биндов."""
        self.keybind_manager.stop()
        self._sound_play_callback = None

    def _register_all_keybinds(self):
        """Зарегистрировать все биндинги из всех звуков."""
        self.keybind_manager.unregister_all()

        for tab_idx, (_, sounds) in enumerate(self.tabs):
            for sound_idx, sound in enumerate(sounds):
                if sound.keybind:
                    self._register_sound_keybind(tab_idx, sound_idx, sound.keybind)

    def _register_sound_keybind(self, tab_idx: int, sound_idx: int, keybind: str):
        """Зарегистрировать биндинг для конкретного звука."""
        if not keybind or not self._sound_play_callback:
            return

        def callback():
            if self._sound_play_callback:
                self._sound_play_callback(tab_idx, sound_idx)

        self.keybind_manager.register(keybind, callback)

    def get_tab_count(self) -> int:
        """Количество вкладок."""
        return len(self.tabs)

    def get_tab_name(self, index: int) -> str:
        """Получить название вкладки."""
        if 0 <= index < len(self.tabs):
            return self.tabs[index][0]
        return ""

    def get_sounds(self, tab_index: int) -> list[SoundInfo]:
        """Получить список звуков во вкладке."""
        if 0 <= tab_index < len(self.tabs):
            return self.tabs[tab_index][1]
        return []

    def add_tab(self, name: str):
        """Добавить вкладку."""
        self.tabs.append((name, []))
        self._save_to_config()

    def remove_tab(self, index: int):
        """Удалить вкладку."""
        if 0 <= index < len(self.tabs) and len(self.tabs) > 1:
            self.tabs.pop(index)
            self._save_to_config()
            self._register_all_keybinds()

    def rename_tab(self, index: int, new_name: str):
        """Переименовать вкладку."""
        if 0 <= index < len(self.tabs):
            sounds = self.tabs[index][1]
            self.tabs[index] = (new_name, sounds)
            self._save_to_config()

    def add_sound(self, tab_index: int, filepath: str) -> Optional[SoundInfo]:
        """Добавить звук во вкладку. Возвращает SoundInfo или None."""
        if not is_supported_format(filepath):
            print(f"[SoundLibrary] Неподдерживаемый формат: {filepath}")
            return None

        if not os.path.exists(filepath):
            print(f"[SoundLibrary] Файл не найден: {filepath}")
            return None

        if 0 <= tab_index < len(self.tabs):
            sound = SoundInfo(path=filepath)
            self.tabs[tab_index][1].append(sound)
            self._save_to_config()
            return sound

        return None

    def remove_sound(self, tab_index: int, sound_index: int):
        """Удалить звук из вкладки."""
        if 0 <= tab_index < len(self.tabs):
            sounds = self.tabs[tab_index][1]
            if 0 <= sound_index < len(sounds):
                sounds.pop(sound_index)
                self._save_to_config()
                self._register_all_keybinds()

    def update_sound(self, tab_index: int, sound_index: int, **kwargs):
        """Обновить параметры звука."""
        if 0 <= tab_index < len(self.tabs):
            sounds = self.tabs[tab_index][1]
            if 0 <= sound_index < len(sounds):
                sound = sounds[sound_index]
                for key, value in kwargs.items():
                    if hasattr(sound, key):
                        setattr(sound, key, value)
                self._save_to_config()
                # Если изменился биндинг — перерегистрируем
                if 'keybind' in kwargs:
                    self._register_all_keybinds()

    def move_sound(self, tab_index: int, from_index: int, to_index: int):
        """Переместить звук внутри вкладки."""
        if 0 <= tab_index < len(self.tabs):
            sounds = self.tabs[tab_index][1]
            if 0 <= from_index < len(sounds) and 0 <= to_index < len(sounds):
                sound = sounds.pop(from_index)
                sounds.insert(to_index, sound)
                self._save_to_config()

    def move_sound_to_tab(self, from_tab: int, sound_index: int, to_tab: int):
        """Переместить звук между вкладками."""
        if (0 <= from_tab < len(self.tabs) and 0 <= to_tab < len(self.tabs)):
            sounds = self.tabs[from_tab][1]
            if 0 <= sound_index < len(sounds):
                sound = sounds.pop(sound_index)
                self.tabs[to_tab][1].append(sound)
                self._save_to_config()
                self._register_all_keybinds()

    def search_sounds(self, query: str) -> list[Tuple[int, int, SoundInfo]]:
        """
        Поиск звуков по имени.
        Возвращает список (tab_index, sound_index, SoundInfo).
        """
        results = []
        query_lower = query.lower().strip()
        if not query_lower:
            return results

        for tab_idx, (_, sounds) in enumerate(self.tabs):
            for sound_idx, sound in enumerate(sounds):
                if (query_lower in sound.display_name.lower() or
                        query_lower in sound.filename.lower()):
                    results.append((tab_idx, sound_idx, sound))

        return results

    def preload_durations_async(self, tab_index: int, callback=None):
        """
        Асинхронно загрузить длительности всех звуков во вкладке.
        callback вызывается после загрузки каждого звука: callback(sound_index).
        """
        def _load():
            sounds = self.get_sounds(tab_index)
            for i, sound in enumerate(sounds):
                _ = sound.duration  # Триггерит ленивую загрузку
                if callback:
                    callback(i)

        thread = threading.Thread(target=_load, daemon=True)
        thread.start()

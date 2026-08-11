#!/usr/bin/env python3
"""
botyaraPAD - Soundpad для Linux (PipeWire)
Точка входа приложения.

Зависимости:
    pip install PyQt5 pygame
    Системные: ffmpeg, pipewire, pipewire-pulse (pactl, parec, pacat)
"""

import sys
import os
import signal

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from config_manager import ConfigManager
from sound_manager import SoundLibrary, cleanup_temp_files
from audio_engine import AudioEngine
from ui_main import MainWindow


def check_dependencies() -> list[str]:
    """Проверить наличие необходимых зависимостей."""
    import shutil

    missing = []

    # Проверяем системные утилиты
    required_tools = {
        "ffmpeg": "ffmpeg — для конвертации аудио",
        "ffprobe": "ffprobe — для получения информации об аудио (часть ffmpeg)",
        "pactl": "pactl — для управления PipeWire/PulseAudio",
        "parec": "parec — для записи аудио (часть pulseaudio-utils)",
        "pacat": "pacat — для воспроизведения аудио (часть pulseaudio-utils)",
    }

    for tool, description in required_tools.items():
        if shutil.which(tool) is None:
            missing.append(description)

    # Проверяем Python-модули
    try:
        import pygame
    except ImportError:
        missing.append("pygame — pip install pygame")

    try:
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        missing.append("PyQt5 — pip install PyQt5")

    return missing


def main():
    """Главная функция запуска botyaraPAD."""

    # Проверяем зависимости
    missing = check_dependencies()
    if missing:
        print("=" * 60)
        print("botyaraPAD — Отсутствуют зависимости!")
        print("=" * 60)
        for dep in missing:
            print(f"  ❌ {dep}")
        print()
        print("Установите недостающие зависимости и попробуйте снова.")
        print("=" * 60)
        sys.exit(1)

    # Обработка Ctrl+C
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Создаём QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("botyaraPAD")
    app.setApplicationDisplayName("botyaraPAD")

    # Поддержка HiDPI (для Wayland)
    try:
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except AttributeError:
        pass  # Старые версии Qt

    # Инициализируем компоненты
    print("[botyaraPAD] Инициализация...")

    config = ConfigManager()
    print(f"[botyaraPAD] Настройки загружены: {config.get('device_name')}")

    library = SoundLibrary(config)
    print(f"[botyaraPAD] Библиотека: {library.get_tab_count()} вкладок")

    engine = AudioEngine(config)

    # Создаём главное окно
    window = MainWindow(config, library, engine)
    window.show()

    print("[botyaraPAD] Запущен!")

    # Запускаем event loop
    exit_code = app.exec_()

    # Очистка
    print("[botyaraPAD] Завершение...")
    cleanup_temp_files()
    print("[botyaraPAD] Готово!")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

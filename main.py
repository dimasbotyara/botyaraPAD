#!/usr/bin/env python3
"""
botyaraPAD - Soundpad for Linux
Главная точка входа приложения.
"""

import sys
import signal
import atexit
import subprocess
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from config_manager import ConfigManager
from sound_manager import SoundLibrary
from audio_engine import AudioEngine, PipeWireVirtualMic
from ui_main import MainWindow


def main():
    """Главная функция запуска приложения."""

    # Включаем высокое DPI (должно быть до создания QApplication)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("botyaraPAD")
    app.setOrganizationName("botyaraPAD")

    print("[botyaraPAD] Запуск...")

    config = ConfigManager()
    library = SoundLibrary(config)
    engine = AudioEngine(config)

    def cleanup_all():
        print("[botyaraPAD] Очистка фоновых процессов и виртуальных устройств...")
        try:
            engine.stop()
        except Exception:
            pass
        try:
            PipeWireVirtualMic.cleanup_orphaned_modules("botyaraPAD")
        except Exception:
            pass
        try:
            subprocess.run(["killall", "-9", "parec", "pacat"], capture_output=True)
        except Exception:
            pass

    atexit.register(cleanup_all)
    app.aboutToQuit.connect(cleanup_all)

    signal.signal(signal.SIGINT, lambda sig, frame: app.quit())
    signal.signal(signal.SIGTERM, lambda sig, frame: app.quit())

    window = MainWindow(config, library, engine)
    window.show()

    print("[botyaraPAD] Готов к работе!")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

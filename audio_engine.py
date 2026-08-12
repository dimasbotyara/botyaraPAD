"""
botyaraPAD - Audio Engine
Создание виртуального микрофона PipeWire, воспроизведение звуков,
маршрутизация аудио (микрофон + динамик).
"""

import subprocess
import threading
import time
import os
import re
import signal
from typing import Optional, Callable

import pygame
import pygame.mixer


class PipeWireVirtualMic:
    """
    Управление виртуальным микрофоном через PipeWire.
    Создаёт null-sink и source через pactl (PipeWire-Pulse совместимость).
    """

    def __init__(self, device_name: str = "botyaraPAD"):
        self.device_name = device_name
        self.sink_module_id: Optional[int] = None
        self.remap_module_id: Optional[int] = None
        self.is_active = False
        self._monitor_source_name = ""
        self._sink_name = ""

    @staticmethod
    def cleanup_orphaned_modules(device_name: str = "botyaraPAD"):
        """Выгрузить абсолютно все унаследованные/застрявшие/дублирующиеся модули botyaraPAD из PipeWire."""
        try:
            result = subprocess.run(
                ["pactl", "list", "modules", "short"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                sanitized_name = re.sub(r'[^a-zA-Z0-9_]', '_', device_name)
                for line in result.stdout.strip().split("\n"):
                    if not line.strip():
                        continue
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        mod_id = parts[0]
                        mod_args = " ".join(parts[1:])
                        if any(k in mod_args for k in [device_name, sanitized_name, "botyaraPAD"]):
                            try:
                                subprocess.run(
                                    ["pactl", "unload-module", mod_id],
                                    capture_output=True,
                                    text=True,
                                    timeout=3
                                )
                                print(f"[PipeWire] Выгружен старый/дублирующий модуль {mod_id}")
                            except Exception:
                                pass
        except Exception as e:
            print(f"[PipeWire] Ошибка очистки старых модулей: {e}")

    def create(self) -> bool:
        """
        Создать виртуальный микрофон.
        Гарантированно выгружает все старые дублирующиеся модули перед созданием.
        """
        # Всегда предварительно чистим любые дубликаты
        self.cleanup_orphaned_modules(self.device_name)
        self.is_active = False

        sanitized_name = re.sub(r'[^a-zA-Z0-9_]', '_', self.device_name)

        # 1. Создаём null-sink — это "приёмник" аудио
        try:
            result = subprocess.run(
                [
                    "pactl", "load-module", "module-null-sink",
                    f"sink_name={sanitized_name}_sink",
                    f"sink_properties=device.description=\"{self.device_name}_Sink\"",
                    "format=s16le",
                    "rate=44100",
                    "channels=2"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                print(f"[PipeWire] Ошибка создания null-sink: {result.stderr}")
                return False

            self.sink_module_id = int(result.stdout.strip())
            self._sink_name = f"{sanitized_name}_sink"
            self._monitor_source_name = f"{sanitized_name}_sink.monitor"
            print(f"[PipeWire] Null-sink создан, module_id={self.sink_module_id}")

        except (subprocess.TimeoutExpired, ValueError, FileNotFoundError) as e:
            print(f"[PipeWire] Ошибка создания null-sink: {e}")
            return False

        # 2. Создаём remap-source — это виртуальный микрофон,
        #    который берёт звук из monitor нашего null-sink
        try:
            result = subprocess.run(
                [
                    "pactl", "load-module", "module-remap-source",
                    f"source_name={sanitized_name}_mic",
                    f"master={self._monitor_source_name}",
                    f"source_properties=device.description=\"{self.device_name}\"",
                    "format=s16le",
                    "rate=44100",
                    "channels=2"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                print(f"[PipeWire] Ошибка создания remap-source: {result.stderr}")
                self._unload_module(self.sink_module_id)
                self.sink_module_id = None
                return False

            self.remap_module_id = int(result.stdout.strip())
            self.is_active = True
            print(f"[PipeWire] Virtual mic создан: {sanitized_name}_mic, module_id={self.remap_module_id}")
            return True

        except (subprocess.TimeoutExpired, ValueError, FileNotFoundError) as e:
            print(f"[PipeWire] Ошибка создания remap-source: {e}")
            self._unload_module(self.sink_module_id)
            self.sink_module_id = None
            return False

    def destroy(self):
        """Удалить виртуальный микрофон и вычистить все модули."""
        self.cleanup_orphaned_modules(self.device_name)
        self.sink_module_id = None
        self.remap_module_id = None
        self.is_active = False
        print("[PipeWire] Виртуальный микрофон удалён")

    def _unload_module(self, module_id: int):
        """Выгрузить модуль PulseAudio/PipeWire."""
        try:
            subprocess.run(
                ["pactl", "unload-module", str(module_id)],
                capture_output=True,
                text=True,
                timeout=5
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"[PipeWire] Ошибка выгрузки модуля {module_id}: {e}")

    @property
    def sink_name(self) -> str:
        """Имя sink'а для воспроизведения в виртуальный микрофон."""
        return self._sink_name

    @property
    def monitor_source(self) -> str:
        """Имя monitor source."""
        return self._monitor_source_name

    @staticmethod
    def get_available_sources() -> list[dict]:
        """
        Получить список доступных источников (микрофонов).
        Возвращает [{"name": ..., "description": ...}, ...]
        """
        sources = []
        try:
            result = subprocess.run(
                ["pactl", "list", "sources", "short"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if not line.strip():
                        continue
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        source_name = parts[1]
                        # Фильтруем monitor-источники (это не микрофоны)
                        if ".monitor" not in source_name:
                            sources.append({
                                "name": source_name,
                                "description": source_name
                            })
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"[PipeWire] Ошибка получения источников: {e}")

        # Получаем описания через pactl list sources
        try:
            result = subprocess.run(
                ["pactl", "list", "sources"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                current_name = ""
                for line in result.stdout.split("\n"):
                    line = line.strip()
                    if line.startswith("Name:"):
                        current_name = line.split(":", 1)[1].strip()
                    elif line.startswith("Description:"):
                        desc = line.split(":", 1)[1].strip()
                        for source in sources:
                            if source["name"] == current_name:
                                source["description"] = desc
                                break
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return sources

    @staticmethod
    def get_available_sinks() -> list[dict]:
        """
        Получить список доступных sink'ов (устройств вывода).
        Возвращает [{"name": ..., "description": ...}, ...]
        """
        sinks = []
        try:
            result = subprocess.run(
                ["pactl", "list", "sinks", "short"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if not line.strip():
                        continue
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        sink_name = parts[1]
                        sinks.append({
                            "name": sink_name,
                            "description": sink_name
                        })
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"[PipeWire] Ошибка получения sink'ов: {e}")

        # Получаем описания
        try:
            result = subprocess.run(
                ["pactl", "list", "sinks"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                current_name = ""
                for line in result.stdout.split("\n"):
                    line = line.strip()
                    if line.startswith("Name:"):
                        current_name = line.split(":", 1)[1].strip()
                    elif line.startswith("Description:"):
                        desc = line.split(":", 1)[1].strip()
                        for sink in sinks:
                            if sink["name"] == current_name:
                                sink["description"] = desc
                                break
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return sinks


class MicPassthrough:
    """
    Прокидывание реального микрофона в виртуальный.
    Использует parec/pacat, направленные строго в виртуальный sink (botyaraPAD_sink).
    Благодаря этому ваш голос попадает в виртуальный микрофон для Discord/игр,
    но НЕ прослушивается в ваших собственных наушниках/динамиках.
    """

    def __init__(self):
        self._is_running = False
        self._lock = threading.Lock()
        self._parec = None
        self._pacat = None

    def start(self, source_name: str, sink_name: str):
        """
        Начать передачу аудио с source_name (реальный микрофон)
        строго в sink_name (виртуальный sink).
        """
        with self._lock:
            if self._is_running:
                self.stop()

            if not source_name or not sink_name:
                print("[MicPassthrough] Не указан источник или приёмник")
                return

            # Выгружаем возможные застрявшие петли module-loopback
            self._unload_existing_loopbacks(sink_name)

            try:
                # parec читает из микрофона
                self._parec = subprocess.Popen(
                    [
                        "parec",
                        "--device", source_name,
                        "--format=s16le",
                        "--rate=44100",
                        "--channels=2",
                        "--latency-msec=20",
                        "--process-time=5ms",
                        "--stream-name=botyaraPAD_mic_in"
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL
                )

                # pacat пишет СТРОГО в виртуальный sink (не в наушники)
                self._pacat = subprocess.Popen(
                    [
                        "pacat",
                        "--device", sink_name,
                        "--format=s16le",
                        "--rate=44100",
                        "--channels=2",
                        "--latency-msec=20",
                        "--process-time=5ms",
                        "--stream-name=botyaraPAD_mic_out"
                    ],
                    stdin=self._parec.stdout,
                    stderr=subprocess.DEVNULL
                )

                self._parec.stdout.close()
                self._is_running = True
                print(f"[MicPassthrough] Запущено изолированно: {source_name} -> {sink_name}")

            except (FileNotFoundError, OSError) as e:
                print(f"[MicPassthrough] Ошибка запуска: {e}")
                self._cleanup_processes()

    def _unload_existing_loopbacks(self, sink_name: str):
        """Гарантированно выгрузить любые старые петли module-loopback."""
        try:
            result = subprocess.run(
                ["pactl", "list", "modules", "short"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if "module-loopback" in line and sink_name in line:
                        parts = line.split("\t")
                        if len(parts) >= 1 and parts[0].isdigit():
                            mod_id = parts[0]
                            try:
                                subprocess.run(
                                    ["pactl", "unload-module", mod_id],
                                    capture_output=True,
                                    text=True,
                                    timeout=3
                                )
                                print(f"[MicPassthrough] Очищен старый loopback модуль {mod_id}")
                            except Exception:
                                pass
        except Exception as e:
            print(f"[MicPassthrough] Ошибка при очистке старых loopback: {e}")

    def stop(self):
        """Остановить передачу."""
        with self._lock:
            self._unload_existing_loopbacks("botyaraPAD_sink")
            self._cleanup_processes()
            self._is_running = False
            print("[MicPassthrough] Остановлено")

    def _cleanup_processes(self):
        """Мгновенно завершить процессы."""
        for proc_name in ('_pacat', '_parec'):
            proc = getattr(self, proc_name, None)
            if proc is not None:
                try:
                    proc.kill()
                except OSError:
                    pass
                setattr(self, proc_name, None)

    @property
    def is_running(self) -> bool:
        return self._is_running


class SoundPlayer:
    """
    Воспроизведение звуков через pygame.mixer.
    Поддерживает одновременное воспроизведение нескольких звуков,
    маршрутизацию в динамик/микрофон/оба.
    """

    # Максимальное количество каналов pygame
    MAX_CHANNELS = 32

    def __init__(self):
        self._initialized = False
        self._channels: dict[int, dict] = {}  # channel_id -> info
        self._next_channel_id = 0
        self._lock = threading.Lock()
        self._master_volume = 1.0
        self._pacat_processes: dict[int, subprocess.Popen] = {}  # channel_id -> pacat process
        self._speaker_sink = ""  # Устройство вывода для динамика

        # Callbacks
        self.on_sound_finished: Optional[Callable[[int], None]] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_running = False

    def initialize(self, speaker_sink: str = ""):
        """Инициализировать pygame.mixer."""
        if self._initialized:
            return

        self._speaker_sink = speaker_sink

        try:
            # Если указан конкретный sink — устанавливаем через environment
            if speaker_sink:
                os.environ['SDL_AUDIODRIVER'] = 'pulseaudio'
                os.environ['PULSE_SINK'] = speaker_sink

            pygame.mixer.init(
                frequency=44100,
                size=-16,
                channels=2,
                buffer=512  # Уменьшили буфер для меньшей задержки
            )
            pygame.mixer.set_num_channels(self.MAX_CHANNELS)
            self._initialized = True
            self._start_monitor()
            print(f"[SoundPlayer] pygame.mixer инициализирован (sink: {speaker_sink or 'default'})")
        except pygame.error as e:
            print(f"[SoundPlayer] Ошибка инициализации pygame.mixer: {e}")

    def shutdown(self):
        """Завершить работу."""
        self._monitor_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)

        self.stop_all()

        if self._initialized:
            try:
                pygame.mixer.quit()
            except pygame.error:
                pass
            self._initialized = False

        # Очищаем environment
        os.environ.pop('PULSE_SINK', None)

        print("[SoundPlayer] Завершён")

    def set_speaker_sink(self, sink_name: str):
        """Изменить устройство вывода (требует переинициализации)."""
        if sink_name != self._speaker_sink:
            was_initialized = self._initialized
            if was_initialized:
                self.shutdown()
            self._speaker_sink = sink_name
            if was_initialized:
                self.initialize(sink_name)

    def _start_monitor(self):
        """Запустить мониторинг завершения воспроизведения."""
        self._monitor_running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _monitor_loop(self):
        """Мониторинг завершения воспроизведения звуков."""
        while self._monitor_running:
            time.sleep(0.05)  # Уменьшили интервал для более быстрой реакции
            with self._lock:
                finished = []
                for ch_id, info in self._channels.items():
                    channel = info.get("channel")
                    if channel and not channel.get_busy():
                        finished.append(ch_id)

                for ch_id in finished:
                    self._cleanup_channel(ch_id)
                    if self.on_sound_finished:
                        try:
                            self.on_sound_finished(ch_id)
                        except Exception as e:
                            print(f"[SoundPlayer] Ошибка в callback: {e}")

    def play(self, wav_path: str, volume: float = 1.0, play_mode: str = "both",
             virtual_sink: str = "", loop: bool = False) -> int:
        """
        Воспроизвести звук.

        Args:
            wav_path: Путь к WAV файлу
            volume: Громкость 0.0-1.0 (уже с учётом индивидуальной)
            play_mode: "both" (микро+динамик), "mic" (только микро), "speaker" (только динамик)
            virtual_sink: Имя виртуального sink'а для вывода в микрофон
            loop: Зациклить воспроизведение

        Returns:
            ID канала (для управления), или -1 при ошибке
        """
        if not self._initialized:
            print("[SoundPlayer] Не инициализирован!")
            return -1

        if not os.path.exists(wav_path):
            print(f"[SoundPlayer] Файл не найден: {wav_path}")
            return -1

        with self._lock:
            channel_id = self._next_channel_id
            self._next_channel_id += 1

        # Загружаем звук
        try:
            sound = pygame.mixer.Sound(wav_path)
        except pygame.error as e:
            print(f"[SoundPlayer] Ошибка загрузки звука: {e}")
            return -1

        # Применяем громкость
        effective_volume = volume * self._master_volume
        sound.set_volume(effective_volume)

        # Находим свободный канал
        channel = pygame.mixer.find_channel()
        if channel is None:
            print("[SoundPlayer] Нет свободных каналов!")
            return -1

        # Определяем количество повторов
        loops = -1 if loop else 0

        # Воспроизводим
        channel.play(sound, loops=loops)

        start_time = time.time()
        duration = sound.get_length() if sound else 0.0

        with self._lock:
            self._channels[channel_id] = {
                "channel": channel,
                "sound": sound,
                "wav_path": wav_path,
                "volume": volume,
                "play_mode": play_mode,
                "loop": loop,
                "start_time": start_time,
                "duration": duration,
                "is_paused": False,
                "pause_start": 0.0,
            }

        # Если нужно отправлять в виртуальный микрофон
        if play_mode in ("both", "mic") and virtual_sink:
            self._start_mic_playback(channel_id, wav_path, effective_volume, virtual_sink, loop)

        print(f"[SoundPlayer] Воспроизведение #{channel_id}: {wav_path}, mode={play_mode}, loop={loop}")
        return channel_id

    def _start_mic_playback(self, channel_id: int, wav_path: str,
                            volume: float, sink_name: str, loop: bool):
        """Запустить воспроизведение в виртуальный sink через ffmpeg+pacat."""
        def _play_to_sink():
            try:
                loop_args = []
                if loop:
                    loop_args = ["-stream_loop", "-1"]

                # ffmpeg читает файл и выводит raw PCM
                ffmpeg_proc = subprocess.Popen(
                    [
                        "ffmpeg",
                        *loop_args,
                        "-i", wav_path,
                        "-f", "s16le",
                        "-ar", "44100",
                        "-ac", "2",
                        "-filter:a", f"volume={volume}",
                        "-"
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL
                )

                # pacat пишет в наш виртуальный sink
                pacat_proc = subprocess.Popen(
                    [
                        "pacat",
                        "--device", sink_name,
                        "--format=s16le",
                        "--rate=44100",
                        "--channels=2",
                        "--latency-msec=10"  # Уменьшили задержку
                    ],
                    stdin=ffmpeg_proc.stdout,
                    stderr=subprocess.DEVNULL
                )

                ffmpeg_proc.stdout.close()

                with self._lock:
                    self._pacat_processes[channel_id] = pacat_proc
                    # Сохраняем ffmpeg процесс тоже для корректного завершения
                    if channel_id in self._channels:
                        self._channels[channel_id]["ffmpeg_proc"] = ffmpeg_proc
                        self._channels[channel_id]["pacat_proc"] = pacat_proc

                pacat_proc.wait()
                ffmpeg_proc.wait()

            except (FileNotFoundError, OSError) as e:
                print(f"[SoundPlayer] Ошибка воспроизведения в sink: {e}")
            finally:
                with self._lock:
                    self._pacat_processes.pop(channel_id, None)

        thread = threading.Thread(target=_play_to_sink, daemon=True)
        thread.start()

    def stop(self, channel_id: int):
        """Остановить конкретный звук."""
        with self._lock:
            if channel_id in self._channels:
                self._cleanup_channel(channel_id)

    def stop_all(self):
        """Остановить все звуки."""
        with self._lock:
            channel_ids = list(self._channels.keys())
            for ch_id in channel_ids:
                self._cleanup_channel(ch_id)

    def _cleanup_channel(self, channel_id: int):
        """Очистить канал (вызывать под lock'ом)."""
        info = self._channels.pop(channel_id, None)
        if info is None:
            return

        # Останавливаем pygame канал
        channel = info.get("channel")
        if channel:
            try:
                channel.stop()
            except pygame.error:
                pass

        # Мгновенно останавливаем ffmpeg/pacat процессы через SIGKILL (без задержек)
        for proc_key in ("pacat_proc", "ffmpeg_proc"):
            proc = info.get(proc_key)
            if proc is not None:
                try:
                    proc.kill()
                except OSError:
                    pass

        # Убираем из pacat_processes
        self._pacat_processes.pop(channel_id, None)

    def pause(self, channel_id: int):
        """Поставить звук на паузу."""
        with self._lock:
            info = self._channels.get(channel_id)
            if not info or info.get("is_paused"):
                return
            channel = info.get("channel")
            if channel:
                try:
                    channel.pause()
                except pygame.error:
                    pass
            for proc_key in ("pacat_proc", "ffmpeg_proc"):
                proc = info.get(proc_key)
                if proc is not None and proc.poll() is None:
                    try:
                        proc.send_signal(signal.SIGSTOP)
                    except OSError:
                        pass
            info["is_paused"] = True
            info["pause_start"] = time.time()

    def unpause(self, channel_id: int):
        """Снять звук с паузы."""
        with self._lock:
            info = self._channels.get(channel_id)
            if not info or not info.get("is_paused"):
                return
            channel = info.get("channel")
            if channel:
                try:
                    channel.unpause()
                except pygame.error:
                    pass
            for proc_key in ("pacat_proc", "ffmpeg_proc"):
                proc = info.get(proc_key)
                if proc is not None and proc.poll() is None:
                    try:
                        proc.send_signal(signal.SIGCONT)
                    except OSError:
                        pass
            pause_duration = time.time() - info.get("pause_start", time.time())
            info["start_time"] = info.get("start_time", time.time()) + pause_duration
            info["is_paused"] = False

    def toggle_pause(self, channel_id: int):
        """Переключить состояние паузы."""
        info = self._channels.get(channel_id)
        if info:
            if info.get("is_paused"):
                self.unpause(channel_id)
            else:
                self.pause(channel_id)

    def get_active_playbacks(self) -> dict:
        """
        Получить активные воспроизведения и прогресс.
        Возвращает dict {channel_id: {"elapsed": float, "duration": float, "progress": float, "is_paused": bool, "wav_path": str}}
        """
        now = time.time()
        result = {}
        with self._lock:
            for ch_id, info in self._channels.items():
                channel = info.get("channel")
                duration = info.get("duration", 0.0)
                is_paused = info.get("is_paused", False)

                if is_paused:
                    elapsed = info.get("pause_start", now) - info.get("start_time", now)
                else:
                    elapsed = now - info.get("start_time", now)

                if duration > 0 and info.get("loop"):
                    elapsed = elapsed % duration

                elapsed = max(0.0, elapsed)
                progress = min(1.0, elapsed / duration) if duration > 0 else 0.0

                is_busy = (channel and channel.get_busy()) or ("ffmpeg_proc" in info) or is_paused
                if is_busy:
                    result[ch_id] = {
                        "elapsed": elapsed,
                        "duration": duration,
                        "progress": progress,
                        "is_paused": is_paused,
                        "wav_path": info.get("wav_path", ""),
                    }
        return result

    def set_master_volume(self, volume: float):
        """
        Установить мастер-громкость (0.0 - 1.0).
        Обновляет громкость всех играющих звуков.
        """
        self._master_volume = max(0.0, min(1.0, volume))
        with self._lock:
            for ch_id, info in self._channels.items():
                channel = info.get("channel")
                sound = info.get("sound")
                if channel and sound and channel.get_busy():
                    effective = info.get("volume", 1.0) * self._master_volume
                    sound.set_volume(effective)

    @property
    def master_volume(self) -> float:
        return self._master_volume

    def get_playing_count(self) -> int:
        """Количество играющих звуков."""
        with self._lock:
            count = 0
            for info in self._channels.values():
                channel = info.get("channel")
                if channel and channel.get_busy():
                    count += 1
            return count

    def is_playing(self, channel_id: int) -> bool:
        """Проверить, играет ли конкретный звук."""
        with self._lock:
            info = self._channels.get(channel_id)
            if info:
                channel = info.get("channel")
                return channel is not None and channel.get_busy()
        return False

    def get_active_channels(self) -> list[int]:
        """Получить список ID активных каналов."""
        with self._lock:
            active = []
            for ch_id, info in self._channels.items():
                channel = info.get("channel")
                if channel and channel.get_busy():
                    active.append(ch_id)
            return active


class AudioEngine:
    """
    Главный аудио-движок — объединяет все компоненты:
    - Виртуальный микрофон (PipeWire)
    - Прокидывание реального микрофона
    - Воспроизведение звуков
    """

    def __init__(self, config_manager):
        self.config = config_manager
        self.virtual_mic = PipeWireVirtualMic(
            device_name=config_manager.get("device_name", "botyaraPAD")
        )
        self.mic_passthrough = MicPassthrough()
        self.player = SoundPlayer()

        self._is_started = False

    def start(self) -> bool:
        """
        Запустить аудио-движок:
        1. Инициализировать pygame.mixer
        2. Создать виртуальный микрофон
        3. Запустить прокидывание реального микрофона (если включено)
        """
        # Получаем устройство вывода
        speaker_sink = self.config.get("speaker_sink", "")

        # Инициализируем плеер
        self.player.initialize(speaker_sink)

        # Устанавливаем мастер-громкость
        master_vol = self.config.get("master_volume", 75) / 100.0
        self.player.set_master_volume(master_vol)

        # Создаём виртуальный микрофон
        device_name = self.config.get("device_name", "botyaraPAD")
        self.virtual_mic.device_name = device_name
        success = self.virtual_mic.create()

        if not success:
            print("[AudioEngine] Не удалось создать виртуальный микрофон!")
            self._is_started = False
            return False

        # Запускаем прокидывание микрофона если включено
        if self.config.get("pass_through_mic", True):
            source_mic = self.config.get("source_mic", "")
            if source_mic:
                self.mic_passthrough.start(source_mic, self.virtual_mic.sink_name)

        self._is_started = True
        print("[AudioEngine] Запущен")
        return True

    def stop(self):
        """Остановить аудио-движок."""
        self.player.stop_all()
        self.mic_passthrough.stop()
        self.virtual_mic.destroy()
        self.player.shutdown()
        self._is_started = False
        print("[AudioEngine] Остановлен")

    def restart(self):
        """Перезапустить (применить новые настройки)."""
        self.stop()
        time.sleep(0.5)
        self.start()

    def set_speaker_sink(self, sink_name: str):
        """Изменить устройство вывода."""
        self.config.set("speaker_sink", sink_name)
        self.player.set_speaker_sink(sink_name)

    def play_sound(self, wav_path: str, volume: float = 1.0,
                   play_mode: str = "both", loop: bool = False) -> int:
        """
        Воспроизвести звук.

        Args:
            wav_path: Путь к WAV-файлу (или конвертированному)
            volume: Индивидуальная громкость 0.0-1.0
            play_mode: "both", "mic", "speaker"
            loop: Зацикливание

        Returns:
            ID канала
        """
        if not self._is_started:
            print("[AudioEngine] Движок не запущен!")
            return -1

        # Определяем play_mode — если не "speaker", нужно играть в виртуальный sink
        virtual_sink = ""
        if play_mode in ("both", "mic") and self.virtual_mic.is_active:
            virtual_sink = self.virtual_mic.sink_name

        # Если режим "mic" — не играем через динамик (не используем pygame)
        if play_mode == "mic":
            return self._play_mic_only(wav_path, volume, virtual_sink, loop)

        # Проверяем overlap
        allow_overlap = self.config.get("allow_overlap", True)
        if not allow_overlap:
            self.player.stop_all()

        return self.player.play(
            wav_path=wav_path,
            volume=volume,
            play_mode=play_mode,
            virtual_sink=virtual_sink,
            loop=loop
        )

    def _play_mic_only(self, wav_path: str, volume: float,
                       sink_name: str, loop: bool) -> int:
        """Воспроизвести только в виртуальный микрофон (без динамика)."""
        if not sink_name:
            print("[AudioEngine] Виртуальный sink не доступен для mic-only режима")
            return -1

        effective_volume = volume * self.player.master_volume

        channel_id = self.player._next_channel_id
        self.player._next_channel_id += 1

        def _play():
            try:
                loop_args = []
                if loop:
                    loop_args = ["-stream_loop", "-1"]

                ffmpeg_proc = subprocess.Popen(
                    [
                        "ffmpeg",
                        *loop_args,
                        "-i", wav_path,
                        "-f", "s16le",
                        "-ar", "44100",
                        "-ac", "2",
                        "-filter:a", f"volume={effective_volume}",
                        "-"
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL
                )

                pacat_proc = subprocess.Popen(
                    [
                        "pacat",
                        "--device", sink_name,
                        "--format=s16le",
                        "--rate=44100",
                        "--channels=2",
                        "--latency-msec=10"
                    ],
                    stdin=ffmpeg_proc.stdout,
                    stderr=subprocess.DEVNULL
                )

                ffmpeg_proc.stdout.close()

                with self.player._lock:
                    self.player._channels[channel_id] = {
                        "channel": None,
                        "sound": None,
                        "wav_path": wav_path,
                        "volume": volume,
                        "play_mode": "mic",
                        "loop": loop,
                        "ffmpeg_proc": ffmpeg_proc,
                        "pacat_proc": pacat_proc,
                    }
                    self.player._pacat_processes[channel_id] = pacat_proc

                pacat_proc.wait()
                ffmpeg_proc.wait()

            except (FileNotFoundError, OSError) as e:
                print(f"[AudioEngine] Ошибка mic-only воспроизведения: {e}")
            finally:
                with self.player._lock:
                    self.player._channels.pop(channel_id, None)
                    self.player._pacat_processes.pop(channel_id, None)
                if self.player.on_sound_finished:
                    try:
                        self.player.on_sound_finished(channel_id)
                    except Exception:
                        pass

        thread = threading.Thread(target=_play, daemon=True)
        thread.start()

        return channel_id

    def stop_sound(self, channel_id: int):
        """Остановить конкретный звук."""
        self.player.stop(channel_id)

    def pause_sound(self, channel_id: int):
        """Поставить звук на паузу."""
        self.player.pause(channel_id)

    def unpause_sound(self, channel_id: int):
        """Снять звук с паузы."""
        self.player.unpause(channel_id)

    def toggle_pause(self, channel_id: int):
        """Переключить паузу звука."""
        self.player.toggle_pause(channel_id)

    def get_active_playbacks(self) -> dict:
        """Получить статус и прогресс всех активных воспроизведений."""
        return self.player.get_active_playbacks()

    def stop_all_sounds(self):
        """Остановить все звуки."""
        self.player.stop_all()

    def set_master_volume(self, volume_percent: int):
        """Установить мастер-громкость (0-100)."""
        self.player.set_master_volume(volume_percent / 100.0)
        self.config.set("master_volume", volume_percent)

    def update_mic_passthrough(self):
        """Обновить состояние прокидывания микрофона."""
        self.mic_passthrough.stop()

        if self.config.get("pass_through_mic", True) and self.virtual_mic.is_active:
            source_mic = self.config.get("source_mic", "")
            if source_mic:
                self.mic_passthrough.start(source_mic, self.virtual_mic.sink_name)

    def update_device_name(self, new_name: str):
        """Обновить имя виртуального устройства (требует перезапуска)."""
        self.config.set("device_name", new_name)
        self.virtual_mic.device_name = new_name

    @property
    def is_active(self) -> bool:
        return self._is_started and self.virtual_mic.is_active

    @property
    def playing_count(self) -> int:
        return self.player.get_playing_count()

    @staticmethod
    def get_sources() -> list[dict]:
        """Получить доступные микрофоны."""
        return PipeWireVirtualMic.get_available_sources()

    @staticmethod
    def get_sinks() -> list[dict]:
        """Получить доступные устройства вывода."""
        return PipeWireVirtualMic.get_available_sinks()

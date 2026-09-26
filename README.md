# 🎧 botyaraPAD

> **A Soundpad alternative for Linux — built for PipeWire, made for gamers, streamers, and memers.**

Play sounds directly into your microphone so everyone in Discord, OBS, or your game can hear them. Your voice and the sound effects mix into one virtual mic — no one hears a difference.

**⚠️ Linux-only. Requires PipeWire (with pipewire-pulse) or PulseAudio.**

---

## ✨ Features

### 🎤 Virtual Microphone (PipeWire-native)
- Creates a real **virtual mic + sink** via `pactl` (pipewire-pulse / PulseAudio compatible)
- Auto-appears in Discord, OBS, Zoom, Teams, browsers, and any app with a device list
- Properly cleaned up on exit — no orphaned modules left behind
- Aggressive deduplication: if a stale `botyaraPAD_sink` is found on startup, it's unloaded first
- Watchdog thread keeps the virtual nodes alive — if PipeWire drops them, they're recreated automatically

### 🔊 Three Play Modes per Sound
- 🎧 **Mic only** — only your voice channel hears it (you don't)
- 🔊 **Speaker only** — only you hear it
- 🔊🎤 **Both** — you and your listeners hear it simultaneously

Set a default mode globally or override it per sound.

### 🎛️ Real Microphone Passthrough
- Your real mic is piped into the virtual sink via `parec` + `pacat`
- **Isolated routing** — the loopback goes *only* to the virtual sink, so your own voice never plays back in your headphones (huge QoL, no echo hell)
- Optional **auto-mute**: silence your real mic while a sound is playing, so listeners get crystal-clear memes without background noise

### 🎼 17+ Supported Audio Formats
MP3, WAV, OGG, FLAC, M4A, AAC, WMA, OPUS, AIFF, AIF, MP2, AC3, AMR, APE, WEBM, MKA, SPX — all auto-converted to WAV on the fly via `ffmpeg`, cached for instant replay.

### ⌨️ Global Hotkeys
- Bind any sound to any key combo (`Ctrl+Shift+A`, `F1`, `Super+M` — anything)
- Works on **Wayland and X11** (uses `pynput`)
- Conflict detection: warns you if the combo is already taken, offers to replace
- Keybind labels shown right in the sound row

### 📑 Tabs & Organization
- Unlimited tabs with custom names
- Rename via double-click, delete via right-click
- Drag sounds between tabs
- Reorder sounds by dragging
- Multi-select (`Ctrl+A`, `Ctrl+Click`, `Shift+Click`) for bulk delete/move
- **Search** across all tabs — instant filter by name or filename

### 🎚️ Per-Sound & Master Volume
- Master volume slider (top bar)
- Per-sound volume slider — **live-updates the playing stream in real time**
- **Scroll-wheel on a sound row** to nudge its volume ±5%
- `pactl set-sink-input-volume` used under the hood for real-time updates without restarting playback

### 🎨 UI Features
- **Grid or list view** — 1, 2, 3, or 4 columns for your sound tiles
- **Dark / Light themes** (Catppuccin Mocha & Latte based)
- Playback progress bar per sound, with elapsed / total time
- Pause / resume individual sounds (`SIGSTOP` / `SIGCONT` on ffmpeg+pacat)
- Stop-all button to kill every playing sound instantly
- Loop mode toggle for the current playing sound
- Native `.desktop` file auto-installed on first run (Wayland icon integration)
- `Ctrl+F` to focus search

### 🖱️ Drag & Drop
- Drop audio files **or whole folders** onto the list — folders are scanned recursively
- Only supported formats are accepted (others silently ignored)

### 🔄 Robust Playback Engine
- Multi-channel mixer via `pygame.mixer` (up to 32 simultaneous sounds)
- Auto-recovery: if SDL context dies (rare but real), the mixer is reinitialized transparently
- All external processes (`ffmpeg`, `pacat`, `parec`) are force-killed with `SIGKILL` on stop — no delay, no zombies

### 🧠 Persistence
- `settings.json` — all global preferences
- `tabs.json` — your tabs, sounds, hotkeys, and per-sound settings
- Window size remembered between launches
- Duration of every sound cached — instant load on next start

### 🛡️ Zero Cloud, Zero Telemetry
- Everything runs locally
- No network calls, no accounts, no analytics
- Your sounds stay on your machine

---

## 🚀 Quick Start

### Prerequisites

You need these system packages:

```bash
# Arch / CachyOS
sudo pacman -S pipewire pipewire-pulse ffmpeg python-pyqt5

# Debian / Ubuntu
sudo apt install pipewire pipewire-pulse ffmpeg python3-pyqt5

# Fedora
sudo dnf install pipewire pipewire-pulseaudio ffmpeg python3-qt5
```

You also need `pactl`, `parec`, and `pacat` — they ship with `pipewire-pulse` / `pulseaudio-utils`.

### Install

```bash
git clone https://github.com/dimasbotyara/botyaraPAD.git
cd botyaraPAD

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### Run

```bash
python main.py
```

On first run, the app creates:
- A virtual microphone named **botyaraPAD**
- A `.desktop` entry in `~/.local/share/applications/`

Then in Discord / OBS / your game:
1. Open audio settings
2. Set **input device** to **botyaraPAD**
3. Done — play sounds in the app, everyone hears them 🎉

---

## 🎮 How to Use

1. **Add sounds** — drag & drop files or folders onto the list, or click **➕ Добавить**
2. **Set up your real mic** — in Settings, pick your physical microphone and enable passthrough
3. **Bind hotkeys** — right-click a sound → ⌨️ Горячая клавиша → press your combo
4. **Play** — click a row, press Enter, double-click, or hit your hotkey
5. **Pick play mode** — 🔊🎤 both / 🔊 speaker only / 🎤 mic only

---

## ⚙️ Settings Overview

### 🎤 Virtual Microphone
| Setting | Description |
|---|---|
| **Device name** | Name of the virtual device (default: `botyaraPAD`) |
| **Real microphone** | Physical mic to pipe into the virtual one |
| **Pass through real mic** | Enable/disable voice passthrough |
| **Mute real mic during playback** | Silence your voice while a sound plays |

### 🔊 Output
| Setting | Description |
|---|---|
| **Speaker sink** | Where the "speaker" side of playback goes (default: system default) |

### 🔊 Playback
| Setting | Description |
|---|---|
| **Default mode** | Both / Speaker / Mic |
| **Allow overlap** | Multiple sounds at once (or stop previous on new) |

### 🎨 Interface
| Setting | Description |
|---|---|
| **Layout** | List, 2, 3, or 4 columns |
| **Theme** | Dark (Catppuccin Mocha) or Light (Catppuccin Latte) |

---

## 🏗️ Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Your mic    │────▶│  MicPassthrough  │────▶│  Virtual Sink   │
│  (parec)     │     │  (parec → pacat) │     │  botyaraPAD_sink│
└──────────────┘     └──────────────────┘     └────────┬────────┘
                                                       │
┌──────────────┐     ┌──────────────────┐              │
│  Sound file  │────▶│  ffmpeg → pacat  │──────────────┤
└──────────────┘     └──────────────────┘              │
                                                       ▼
                        ┌──────────────────────────────────────┐
                        │  Virtual Mic "botyaraPAD"            │
                        │  (module-remap-source)               │
                        └──────────────────┬───────────────────┘
                                           │
                                           ▼
                        ┌──────────────────────────────────────┐
                        │  Discord / OBS / Game / Browser      │
                        └──────────────────────────────────────┘
```

**Key insight:** the mic passthrough routes *strictly to the virtual sink*, never to your speakers. That's what makes it listenable in Discord but silent in your own headphones.

---

## 📁 Project Structure

```
botyaraPAD/
├── main.py              # 🎯 Entry point, desktop integration, signal handling
├── audio_engine.py      # 🔊 PipeWire virtual mic + mic passthrough + sound player
├── sound_manager.py     # 📚 Sound library, ffmpeg conversion, keybind manager
├── config_manager.py    # 💾 settings.json + tabs.json persistence
├── ui_main.py           # 🖼️ Main window, tabs, signals, playback orchestration
├── ui_settings.py       # ⚙️ Settings dialog
├── ui_widgets.py        # 🎨 Custom widgets: sound rows, top bar, themes, dialogs
├── requirements.txt
├── assets/
│   └── icon.png         # App icon (auto-installed as .desktop)
├── settings.json        # (auto-created) Global settings
└── tabs.json            # (auto-created) Tabs + sounds + hotkeys
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **GUI** | PyQt5 |
| **Playback** | pygame.mixer (SDL) + ffmpeg + pacat |
| **Mic routing** | parec + pacat (isolated) |
| **Virtual devices** | pactl (PipeWire-Pulse / PulseAudio) |
| **Audio probing** | ffprobe |
| **Hotkeys** | pynput (Wayland & X11) |
| **Persistence** | JSON |

---

## 🔧 Advanced

### Custom virtual device name
Change it in Settings — the old device is fully cleaned up and a new one is created.

### Playing from a script
Not exposed as a CLI yet — but you can `pynput`-style trigger via the keybind system, or call `AudioEngine.play_sound()` if you fork it.

### Bundled sounds
`botyaraPAD` doesn't ship any sounds. You bring your own (mp3/wav/ogg/flac/…). Drop them in, done.

### Auto-start on login
Create `~/.config/autostart/botyaraPAD.desktop`:
```ini
[Desktop Entry]
Type=Application
Name=botyaraPAD
Exec=/path/to/botyaraPAD/.venv/bin/python /path/to/botyaraPAD/main.py
X-GNOME-Autostart-enabled=true
```

---

## 🐛 Troubleshooting

**Virtual mic doesn't appear in Discord**
- Make sure `pipewire-pulse` is running: `systemctl --user status pipewire-pulse`
- Check `pactl list sources short | grep botyaraPAD` — if it's missing, restart the app
- Discord sometimes needs to be restarted after a new device appears

**No sound in Discord, but I hear it locally**
- Set play mode to **both** or **mic only**
- Check Discord's input device is set to **botyaraPAD**

**My voice echoes back into my headphones**
- Make sure you're not using a `module-loopback` manually — `botyaraPAD` routes audio only to its own sink, no echo

**Mic passthrough stops after a while**
- The watchdog recreates it — check the console for `[AudioEngine Watchdog]` lines
- If it happens constantly, your `parec` is dying; check `dmesg` or your mic's stability

**ffmpeg missing**
- `sudo pacman -S ffmpeg` (or your distro's equivalent)
- `botyaraPAD` needs both `ffmpeg` and `ffprobe`

---

## ⚠️ Disclaimer

`botyaraPAD` is for **legal and ethical use only**. Don't use it to grief, harass, or spam. Also don't use it to play copyrighted audio in public streams without permission. You are responsible for how you use it.

---

## 📜 License

MIT — see [LICENSE](LICENSE) for details.

---

## 👤 Author

**dimasbotyara** — [@dimasbotyara](https://github.com/dimasbotyara)

Made with 🎧, ☕, and a deep hatred for the Linux audio stack… which I then proceeded to master anyway.

---

<div align="center">

**If you used this to blast All Star into a Discord call, drop a ⭐**

</div>

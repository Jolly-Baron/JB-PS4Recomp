<div align="center">
  <img src="https://raw.githubusercontent.com/Jolly-Baron/.github/main/jollybaron.jpg" alt="Jolly Baron Logo" width="400">
  <br>
  <a href="https://boosty.to/jollybaron/donate">
    <img src="https://img.shields.io/badge/❤️_Support_on_Boosty-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white" alt="Donate on Boosty">
  </a>

# JB PS4Recomp

**A clone-and-play launcher + runtime that runs your own PS4 dumps natively on Windows (Vulkan).**

Works **completely offline**. Bundled Python and runtime — no installs, no dependencies. Add a legally obtained dump, press Play.

---

## ✨ Features

- **Clone-and-play** — bundled Python + cryptography + runtime; nothing to install
- **PKG installer** — extract `.pkg` (retail keys bundled), auto-detect title & CUSA, auto-add profile
- **Per-game profiles** — game folder, graphics, controls and env saved per title
- **Graphics** — render resolution, upscalers (FSR 3.1 / TAA / DLSS), FXAA, RCAS sharpening, VSync, FPS limit
- **Controls** — keyboard/mouse button capture with live preview; gamepad remap via raw map
- **Live title-bar stats** — honest presented FPS + CPU / GPU / RAM while you play
- **Save backup** — automatic save snapshots before each run (optional)
- **Logs** — one click opens the logs folder; crash tail surfaced on exit
- **Dark single-instance UI** — geometry remembered, game icon taken from the dump

### Developer notes

- Main development and testing was done on **Exist Archive (CUSA04726)** on a GTX 1660 Ti.
- The runtime is derived from **shadPS4** (GPL-2.0); full source lives in the [`source`](../../tree/source) branch.
- DLSS needs NVIDIA tensor cores; FSR 4 needs a capable GPU — otherwise the runtime falls back to FSR 3.1.

---

## 📦 Installation

### Quick setup (recommended)

1. **Clone the repository**

```
git clone https://github.com/Jolly-Baron/JB-PS4Recomp.git
cd JB-PS4Recomp
```

2. **Launch**

Double-click `JB-PS4Recomp.bat`. No setup script, no Python install — everything is bundled.

3. **Add your dump**

Press **Add**, browse to your extracted game folder (with `sce_sys/` and `eboot.bin`), or use **Install pkg** to extract a `.pkg` first.

4. **Play**

Select the game, press **Play**.

---

## 🚀 Usage

- **Graphics tab** — window mode, FPS limit, render resolution, upscaler, sharpening.
- **Controls tab** — confirm button, input mode, mouse look; **Capture** to remap keyboard/mouse by pressing keys.
- **Debug tab** — paths, env overrides, raw pad/key maps, advanced upscalers, command preview.
- **Open logs** — opens the logs folder; pick the newest log.

---

## ⚙️ Performance tips

- **GPU-bound title?** Lower render resolution (720p) and enable FSR 3.1 for headroom.
- **No tensor cores** (e.g. GTX 1660 Ti): DLSS unavailable; use FSR 3.1 / TAA.
- **VSync + FPS limit** cap presented frames; the title-bar FPS shows real presented frames, not engine ticks.

---

## 📁 Project structure

```
JB-PS4Recomp/
├── launcher.py            # UI + glue
├── theme.py               # dark theme / widgets
├── runtime.py             # process launch, profiles, save backup hooks
├── extract_pkg.py         # PKG extractor UI
├── key_capture.py         # keyboard/mouse capture modal
├── JB-PS4Recomp.bat       # entry point (bundled python)
├── backend/               # run.py, scripts, patches, runtime exe
├── python/                # bundled interpreter + cryptography (PSF / Apache / BSD)
├── assets/                # logo + icon (CC BY 4.0)
├── licenses/              # third-party licenses
├── games/                 # your dumps (not included, add your own)
└── profiles/ logs/ cache/ # auto-created, never committed
```

> **Note:** `games/` is not included. Place your own legally obtained dumps there. Saves, logs, profiles and cache are auto-created and **never committed**.

---

## ⚙️ Requirements

- Windows 10/11 x64
- Vulkan-capable GPU
- No Python / no installs (bundled)
- Your own legally obtained PS4 dump

---

## 💖 Support

If you find this project useful and would like to support its development, you can donate via Boosty:

- **Boosty**: https://boosty.to/jollybaron

---

## ⚖️ License

**GPL-2.0-or-later** (runtime derived from shadPS4). Launcher/UI © Jolly Baron.
Art **CC BY 4.0**; bundled Python **PSF**; cryptography **Apache/BSD** (see `licenses/`).

Complete corresponding source: [`source` branch](../../tree/source).

This tool is intended for use with **legally obtained** game dumps. Users are responsible for complying with all applicable laws. The author assumes no liability for misuse.

# JB PS4Recomp launcher UI layer.
# Copyright (c) 2026 Jolly Baron.
# SPDX-License-Identifier: GPL-2.0-or-later
"""JB PS4Recomp - launcher (UI and glue)."""
import ctypes
import json
import os
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from theme import (C, MONO, UI, apply_theme, dark_text, button, segmented, Scroll)
from runtime import (ROOT, PROFILES_DIR, LOGO_PATH, ICON_PATH, find_python,
                     GameProcess, ini_read, ini_write_keys, read_tail,
                     load_profiles, write_profile, delete_profile, slug,
                     png_to_bmp, kill_process_tree, read_sfo)

DISPLAY_MODES = ["Windowed", "Borderless", "Fullscreen"]
FPS_LIMITS = ["Unlimited", "30", "60", "120", "240"]
RENDER_RESOLUTIONS = ["native", "720p", "1440p", "1800p", "4K"]
UPSCALERS = ["off", "taa", "fsr3", "dlss"]
ALL_UPSCALERS = ["off", "taa", "fsr3", "dlss", "fsr4", "fsr411"]
PRESETS = ["Native AA", "Quality", "Balanced", "Performance", "Ultra Performance"]
OUTPUT_RES = ["1280x720", "1920x1080", "2560x1440", "3840x2160"]
ANISOTROPY = ["Game default", "2", "4", "8", "16"]
ENGINE_FPS = ["60", "120", "240"]
SHADOWS = ["standard", "high"]
CONFIRM_BUTTONS = ["Circle", "Cross"]
INPUT_MODES = ["Auto", "Pad", "Keyboard"]
UI_SETTINGS = ROOT / "launcher_settings.json"
_MUTEX = None


def dump_info(game):
    sfo = read_sfo(Path(game) / "sce_sys" / "param.sfo")
    title = sfo.get("TITLE") or ""
    tid = sfo.get("TITLE_ID") or ""
    ok = (Path(game) / "eboot.bin").is_file() and bool(sfo)
    return title, tid, ok


class App:
    def __init__(self, root):
        self.root = root
        root.title("JB PS4Recomp")
        root.geometry("1140x800")
        root.minsize(960, 620)
        apply_theme(root)
        self._load_geometry()

        self.logo = None
        self.icon = None
        self.profiles = []
        self.profile = None
        self.busy = False
        self.vars = {}
        self.dirty = False
        self.gp = GameProcess()
        self._stop_requested = False

        self._load_brand()
        self._header()
        self._tabs()
        self._reload_profiles()
        root.protocol("WM_DELETE_WINDOW", self._close)

    def _load_geometry(self):
        try:
            g = json.loads(UI_SETTINGS.read_text(encoding="utf-8")).get("geometry")
            if g:
                self.root.geometry(g)
        except Exception:
            pass

    def _save_geometry(self):
        try:
            UI_SETTINGS.write_text(json.dumps({"geometry": self.root.geometry()}, indent=2),
                                   encoding="utf-8")
        except Exception:
            pass

    def _load_brand(self):
        if sys.platform == "win32":
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "JollyBaron.PS4Recomp.Launcher")
            except Exception:
                pass
        try:
            if LOGO_PATH.exists():
                img = tk.PhotoImage(file=str(LOGO_PATH))
                factor = max(2, round(img.height() / 100))
                self.logo = img.subsample(factor, factor)
        except Exception:
            self.logo = None
        try:
            if ICON_PATH.exists():
                self.icon = tk.PhotoImage(file=str(ICON_PATH))
                self.root.iconphoto(True, self.icon)
        except Exception:
            self.icon = None

    def _header(self):
        head = tk.Frame(self.root, bg=C["bg"])
        head.pack(fill=tk.X)
        tk.Frame(head, bg=C["gold"], height=2).pack(fill=tk.X)
        tk.Frame(head, bg=C["accent"], height=1).pack(fill=tk.X)

        inner = ttk.Frame(head, padding=(16, 10, 16, 8))
        inner.pack(fill=tk.X)

        left = ttk.Frame(inner)
        left.pack(side=tk.LEFT)
        if self.logo is not None:
            tk.Label(left, image=self.logo, bg=C["bg"], borderwidth=0,
                     highlightthickness=0).pack(side=tk.LEFT, padx=(0, 14))
        text = ttk.Frame(left)
        text.pack(side=tk.LEFT)
        ttk.Label(text, text="JB PS4Recomp", style="Title.TLabel").pack(anchor="w")
        ttk.Label(text, text="JOLLY BARON  /  STATIC RECOMPILATION", style="Brand.TLabel").pack(anchor="w")

        right = ttk.Frame(inner)
        right.pack(side=tk.RIGHT)
        self.lbl_state = ttk.Label(right, text="", foreground=C["muted"])
        self.lbl_state.pack(anchor="e")

        bar = ttk.Frame(self.root, padding=(16, 0, 16, 4))
        bar.pack(fill=tk.X)
        ttk.Label(bar, text="Game").pack(side=tk.LEFT)
        self.var_profile = tk.StringVar()
        self.cmb = ttk.Combobox(bar, textvariable=self.var_profile, state="readonly", width=34)
        self.cmb.pack(side=tk.LEFT, padx=8)
        self.cmb.bind("<<ComboboxSelected>>", lambda e: self._refresh_profile())
        button(bar, "Add", self.do_add_game, "ghost").pack(side=tk.LEFT, padx=2)
        button(bar, "Remove", self.do_remove_game, "ghost").pack(side=tk.LEFT, padx=2)

        self.btn_play = button(bar, "Play", self.do_play, "primary")
        self.btn_play.pack(side=tk.LEFT, padx=(16, 4))
        self.btn_stop = button(bar, "Stop", self.do_stop, "danger")
        self.btn_stop.pack(side=tk.LEFT, padx=4)
        self.btn_stop.configure(state=tk.DISABLED)
        button(bar, "Open logs", self.do_open_logs, "ghost").pack(side=tk.LEFT, padx=4)
        button(bar, "Install pkg", self.do_install_pkg, "ghost").pack(side=tk.LEFT, padx=4)

        # second row: the game folder lives here now, no Settings tab
        self.vars["game_dir"] = tk.StringVar()
        bar2 = ttk.Frame(self.root, padding=(16, 0, 16, 8))
        bar2.pack(fill=tk.X)
        bar2.columnconfigure(1, weight=1)
        ttk.Label(bar2, text="Game folder").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ge = tk.Entry(bar2, textvariable=self.vars["game_dir"],
                      bg=C["field"], fg=C["ink"], insertbackground=C["accent"],
                      relief=tk.FLAT, highlightthickness=1,
                      highlightbackground=C["line"], highlightcolor=C["accent"], font=MONO)
        ge.grid(row=0, column=1, sticky="ew", padx=(0, 6))
        ge.bind("<KeyRelease>", lambda ev: self._changed())
        button(bar2, "Browse", self._browse_game, "ghost").grid(row=0, column=2, padx=(0, 10))
        button(bar2, "Save", self.save_settings, "primary").grid(row=0, column=3, padx=2)
        button(bar2, "Revert", self.revert_settings, "ghost").grid(row=0, column=4, padx=(2, 10))
        self.lbl_dirty = tk.Label(bar2, text="", bg=C["bg"], fg=C["muted"], font=UI)
        self.lbl_dirty.grid(row=0, column=5, sticky="e")

        ttk.Separator(self.root).pack(fill=tk.X, padx=16)

    def _tabs(self):
        self.nb = ttk.Notebook(self.root, padding=10)
        self.nb.pack(fill=tk.BOTH, expand=True)

        self.tab_graphics = ttk.Frame(self.nb)
        self.nb.add(self.tab_graphics, text="Graphics")
        self._graphics_ui()

        self.tab_controls = ttk.Frame(self.nb)
        self.nb.add(self.tab_controls, text="Controls")
        self._controls_ui()

        self.tab_debug = ttk.Frame(self.nb)
        self.nb.add(self.tab_debug, text="Debug")
        self._debug_ui()

    def _group(self, parent, title, note=None):
        wrap = tk.Frame(parent, bg=C["panel"], highlightthickness=1,
                        highlightbackground=C["line"], borderwidth=0)
        wrap.pack(fill=tk.X, pady=(0, 12))
        head = ttk.Frame(wrap, style="Panel.TFrame", padding=(14, 10, 14, 6))
        head.pack(fill=tk.X)
        ttk.Label(head, text=title.upper(), style="Head.TLabel").pack(side=tk.LEFT)
        if note:
            ttk.Label(head, text=note, style="Hint.TLabel").pack(side=tk.RIGHT)
        body = ttk.Frame(wrap, style="Panel.TFrame", padding=(14, 0, 14, 12))
        body.pack(fill=tk.X)
        return body

    def _row(self, parent, label, hint=None):
        r = ttk.Frame(parent, style="Panel.TFrame")
        r.pack(fill=tk.X, pady=4)
        left = ttk.Frame(r, style="Panel.TFrame")
        left.pack(side=tk.LEFT)
        ttk.Label(left, text=label, style="Panel.TLabel").pack(anchor="w")
        if hint:
            ttk.Label(left, text=hint, style="Hint.TLabel").pack(anchor="w")
        right = ttk.Frame(r, style="Panel.TFrame")
        right.pack(side=tk.RIGHT)
        return right

    def _entry(self, parent, var, width=34):
        e = tk.Entry(parent, textvariable=var, width=width,
                     bg=C["field"], fg=C["ink"], insertbackground=C["accent"],
                     relief=tk.FLAT, highlightthickness=1,
                     highlightbackground=C["line"], highlightcolor=C["accent"], font=MONO)
        e.bind("<KeyRelease>", lambda ev: self._changed())
        return e

    def _combo(self, parent, key, values, default, width=16):
        self.vars[key] = tk.StringVar(value=default)
        cb = ttk.Combobox(parent, textvariable=self.vars[key], state="readonly",
                          width=width, values=values)
        cb.pack()
        cb.bind("<<ComboboxSelected>>", lambda e: self._changed())
        return cb

    def _check(self, parent, key, label, default=True):
        self.vars[key] = tk.BooleanVar(value=default)
        ttk.Checkbutton(parent, text=label, variable=self.vars[key],
                        command=self._changed).pack()

    def _graphics_ui(self):
        outer = ttk.Frame(self.tab_graphics)
        outer.pack(fill=tk.BOTH, expand=True)
        sc = Scroll(outer)
        sc.pack(fill=tk.BOTH, expand=True)
        page = sc.body

        g = self._group(page, "Display", "window and frame rate")
        r = self._row(g, "Window mode", "F11 switches while the game runs")
        self.vars["display_mode"] = tk.StringVar(value="Borderless")
        segmented(r, self.vars["display_mode"], [(m, m) for m in DISPLAY_MODES], self._changed).pack()
        r = self._row(g, "FPS limit", "0 = unlimited")
        self.vars["fps_limit"] = tk.StringVar(value="Unlimited")
        segmented(r, self.vars["fps_limit"], [(f, f) for f in FPS_LIMITS], self._changed).pack()
        r = self._row(g, "VSync", "syncs to the monitor")
        self._check(r, "vsync", "On")

        g = self._group(page, "Scaling", "internal resolution and upscaler")
        r = self._row(g, "Render resolution", "native = game's own")
        self._combo(r, "render_resolution", RENDER_RESOLUTIONS, "native")
        r = self._row(g, "Upscaler", "off = game's FXAA")
        self._combo(r, "upscaler", UPSCALERS, "off")
        r = self._row(g, "Upscale preset", "quality vs performance")
        self._combo(r, "preset", PRESETS, "Native AA")
        r = self._row(g, "Output resolution", "the window's size")
        self._combo(r, "output_res", OUTPUT_RES, "1920x1080")

        g = self._group(page, "Image", "anti-aliasing and sharpening")
        r = self._row(g, "Game FXAA", "the game's own AA")
        self._check(r, "fxaa", "On")
        r = self._row(g, "RCAS sharpening", "FidelityFX CAS")
        self._check(r, "rcas", "On")

        g = self._group(page, "Engine", "needs restart to apply")
        r = self._row(g, "Engine FPS", "60 = game's own, 120/240 = patches")
        self.vars["engine_fps"] = tk.StringVar(value="60")
        segmented(r, self.vars["engine_fps"], [(f, f) for f in ENGINE_FPS], self._changed).pack()
        r = self._row(g, "Shadow quality", "standard = game's own")
        self.vars["shadow_quality"] = tk.StringVar(value="standard")
        segmented(r, self.vars["shadow_quality"], [(s, s) for s in SHADOWS], self._changed).pack()

        foot = tk.Frame(page, bg=C["bg"])
        foot.pack(fill=tk.X, pady=(4, 16))
        button(foot, "Reload from ini", self.load_graphics_from_ini, "ghost").pack(side=tk.LEFT, padx=6)
        button(foot, "Save to ini", self.save_graphics_to_ini, "primary").pack(side=tk.LEFT, padx=6)
        ttk.Label(foot, text="Saved to the backend ps4recomp.ini; the in-game menu shares it.",
                  foreground=C["dim"], font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=10)

    def _controls_ui(self):
        outer = ttk.Frame(self.tab_controls)
        outer.pack(fill=tk.BOTH, expand=True)
        sc = Scroll(outer)
        sc.pack(fill=tk.BOTH, expand=True)
        page = sc.body

        g = self._group(page, "Menu buttons", "confirm and cancel in dialogs")
        r = self._row(g, "Menu confirm button", "Circle = OK (JP), Cross = OK (West)")
        self.vars["confirm"] = tk.StringVar(value="Circle")
        segmented(r, self.vars["confirm"], [(c, c) for c in CONFIRM_BUTTONS], self._changed).pack()

        g = self._group(page, "Input device", "what controls the game")
        r = self._row(g, "Input mode", "Auto picks the best available device")
        self.vars["input"] = tk.StringVar(value="Auto")
        segmented(r, self.vars["input"], [(m, m) for m in INPUT_MODES], self._changed).pack()
        r = self._row(g, "Mouse look", "cursor captured for camera control")
        self._check(r, "mouse_look", "On")

        g = self._group(page, "Mouse", "sensitivity and inversion")
        r = self._row(g, "Mouse sensitivity", "default 1.0")
        row = ttk.Frame(r, style="Panel.TFrame"); row.pack()
        self.vars["mouse_sens"] = tk.StringVar(value="1.0")
        self._entry(row, self.vars["mouse_sens"], width=10).pack(side=tk.LEFT)
        r = self._row(g, "Invert mouse Y", "flip vertical axis")
        self._check(r, "mouse_invert_y", "On", default=False)
        g = self._group(page, "Button mapping", "click Capture, then press a key or mouse button")
        r = self._row(g, "Current key map", "captured tokens; raw strings live in Debug")
        self.lbl_keymap = ttk.Label(r, text="", style="Hint.TLabel")
        self.lbl_keymap.pack(side=tk.LEFT)
        button(r, "Capture", self.do_capture_map, "primary").pack(side=tk.RIGHT)

    def _debug_ui(self):
        outer = ttk.Frame(self.tab_debug)
        outer.pack(fill=tk.BOTH, expand=True)
        sc = Scroll(outer)
        sc.pack(fill=tk.BOTH, expand=True)
        page = sc.body

        g = self._group(page, "Paths", "backend, runner and log")
        for key, label, hint, browse in (
            ("backend_dir", "Backend directory", "where run.py lives", self._browse_backend),
            ("runner", "Runner", "the script that launches the game", self._browse_runner),
            ("log_file", "Log file", "relative to the launcher folder", self._browse_log),
        ):
            r = self._row(g, label, hint)
            row = ttk.Frame(r, style="Panel.TFrame")
            row.pack()
            self.vars[key] = tk.StringVar()
            self._entry(row, self.vars[key]).pack(side=tk.LEFT, padx=(0, 6))
            button(row, "Browse", browse, "ghost").pack(side=tk.LEFT)

        g = self._group(page, "Environment", "extra variables passed to the game")
        r = self._row(g, "Overrides", "KEY=VALUE, one per line")
        self.vars["env"] = tk.Text(r, height=5, wrap=tk.NONE)
        dark_text(self.vars["env"])
        self.vars["env"].pack(fill=tk.X, pady=4)
        self.vars["env"].bind("<KeyRelease>", lambda ev: self._changed())

        g = self._group(page, "Advanced graphics", "readback and filtering")
        r = self._row(g, "Refresh rate Hz", "0 keeps the desktop's")
        row = ttk.Frame(r, style="Panel.TFrame"); row.pack()
        self.vars["refresh_rate"] = tk.StringVar(value="0")
        self._entry(row, self.vars["refresh_rate"], width=10).pack(side=tk.LEFT)
        r = self._row(g, "RCAS strength %", "0-100, default 75")
        row = ttk.Frame(r, style="Panel.TFrame"); row.pack()
        self.vars["rcas_strength"] = tk.StringVar(value="75")
        self._entry(row, self.vars["rcas_strength"], width=10).pack(side=tk.LEFT)
        r = self._row(g, "Anisotropy", "0 = game's own")
        self._combo(r, "anisotropy", ANISOTROPY, "16")
        r = self._row(g, "Upscaler (advanced)", "FSR 4 needs a capable GPU; otherwise falls back to FSR 3.1")
        cb = ttk.Combobox(r, textvariable=self.vars["upscaler"], state="readonly", width=16, values=ALL_UPSCALERS)
        cb.pack()
        cb.bind("<<ComboboxSelected>>", lambda e: self._changed())
        for key, label in (("async_shaders", "Async shaders"),
                           ("deferred_readback", "Deferred readback"),
                           ("stale_readback", "Stale readback")):
            r = self._row(g, label, "")
            self._check(r, key, "On")

        g = self._group(page, "Advanced controls", "gyro and button remap")
        r = self._row(g, "Gyro sensitivity", "default 1.4, gamepad only")
        row = ttk.Frame(r, style="Panel.TFrame"); row.pack()
        self.vars["gyro_sens"] = tk.StringVar(value="1.4")
        self._entry(row, self.vars["gyro_sens"], width=10).pack(side=tk.LEFT)
        r = self._row(g, "Pad map", "e.g. cross=b,circle=a")
        row = ttk.Frame(r, style="Panel.TFrame"); row.pack()
        self.vars["pad_map"] = tk.StringVar()
        self._entry(row, self.vars["pad_map"]).pack(fill=tk.X, expand=True)
        r = self._row(g, "Key map", "e.g. cross=Q,square=E|Mouse Left")
        row = ttk.Frame(r, style="Panel.TFrame"); row.pack()
        self.vars["key_map"] = tk.StringVar()
        self._entry(row, self.vars["key_map"]).pack(fill=tk.X, expand=True)
        button(page, "Clear remaps", self.clear_remaps, "ghost").pack(anchor="w", padx=6, pady=4)

        g = self._group(page, "Command preview", "what Play will run")
        self.txt_cmd = tk.Text(g, wrap=tk.NONE, height=12)
        dark_text(self.txt_cmd)
        sb = ttk.Scrollbar(g, orient=tk.VERTICAL, command=self.txt_cmd.yview)
        self.txt_cmd.configure(yscrollcommand=sb.set)
        self.txt_cmd.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        for tag, color in (("good", C["good"]), ("warn", C["warn"]), ("bad", C["bad"]),
                           ("dim", C["muted"]), ("key", C["accent"])):
            self.txt_cmd.tag_configure(tag, foreground=color)

    def do_capture_map(self):
        if self.vars["input"].get() == "Pad":
            messagebox.showinfo("Capture mapping",
                "Gamepad capture needs the parser confirmed (RB2). "
                "Edit the raw Pad map in Debug for now.")
            return
        from key_capture import capture_mapping
        capture_mapping(self.root, self.vars, self._changed)
        self.lbl_keymap.configure(text=self.vars["key_map"].get() or "(none)")
    def _browse_backend(self):
        p = filedialog.askdirectory(title="Select backend directory")
        if p:
            self.vars["backend_dir"].set(p); self._changed(); self.load_graphics_from_ini()

    def _browse_runner(self):
        p = filedialog.askopenfilename(title="Select runner",
                                       filetypes=[("Python scripts", "*.py"), ("All files", "*.*")])
        if p:
            self.vars["runner"].set(p); self._changed()

    def _browse_game(self):
        p = filedialog.askdirectory(title="Select game directory")
        if p:
            self.vars["game_dir"].set(p); self._changed()

    def _browse_log(self):
        p = filedialog.asksaveasfilename(title="Select log file", defaultextension=".log",
                                         filetypes=[("Log files", "*.log"), ("All files", "*.*")])
        if p:
            self.vars["log_file"].set(p); self._changed()

    def clear_remaps(self):
        self.vars["pad_map"].set(""); self.vars["key_map"].set(""); self._changed()

    def _backend_path(self):
        b = self.vars["backend_dir"].get() or "backend"
        p = Path(b)
        return p if p.is_absolute() else (ROOT / p)

    def _resolve_window_icon(self, game):
        studio = self._backend_path() / "launcher" / "window.bmp"
        src = Path(game) / "sce_sys" / "icon0.png"
        cache = ROOT / "cache" / "icons" / (Path(game).name + ".bmp")
        if src.is_file():
            try:
                if not cache.is_file() or src.stat().st_mtime > cache.stat().st_mtime:
                    png_to_bmp(src, cache, 64)
            except Exception:
                pass
        if cache.is_file():
            return str(cache)
        return str(studio) if studio.is_file() else None

    def gfx_ini_path(self):
        return self._backend_path() / "ps4recomp.ini"

    def load_graphics_from_ini(self):
        v = ini_read(self.gfx_ini_path())
        mode = v.get("display_mode", "borderless")
        self.vars["display_mode"].set(next((m for m in DISPLAY_MODES if m.lower() == mode), "Borderless"))
        self.vars["refresh_rate"].set(v.get("refresh_rate", "0"))
        self.vars["vsync"].set(v.get("vsync", "1") != "0")
        fps = v.get("fps_limit", "0")
        self.vars["fps_limit"].set("Unlimited" if fps == "0" else (fps if fps in FPS_LIMITS else "Unlimited"))
        for key, allowed, fallback in (
            ("render_resolution", RENDER_RESOLUTIONS, "native"),
            ("upscaler", ALL_UPSCALERS, "off"),
            ("preset", PRESETS, "Native AA"),
            ("output_res", OUTPUT_RES, "1920x1080"),
            ("engine_fps", ENGINE_FPS, "60"),
            ("shadow_quality", SHADOWS, "standard"),
        ):
            val = v.get(key, fallback)
            self.vars[key].set(val if val in allowed else fallback)
        aniso = v.get("anisotropy", "16")
        self.vars["anisotropy"].set("Game default" if aniso == "0"
                                    else (aniso if aniso in ANISOTROPY else "16"))
        self.vars["rcas"].set(v.get("rcas", "1") != "0")
        try:
            strength = max(0, min(100, int(v.get("rcas_strength", "75"))))
        except ValueError:
            strength = 75
        self.vars["rcas_strength"].set(str(strength))
        self.vars["fxaa"].set(v.get("fxaa", "1") != "0")
        for key in ("async_shaders", "deferred_readback", "stale_readback"):
            self.vars[key].set(v.get(key, "1") != "0")

    def collect_graphics(self):
        try:
            strength = max(0, min(100, int(self.vars["rcas_strength"].get())))
        except ValueError:
            strength = 75
        try:
            refresh = max(0, int(self.vars["refresh_rate"].get()))
        except ValueError:
            refresh = 0
        fps = self.vars["fps_limit"].get()
        aniso = self.vars["anisotropy"].get()
        return {
            "display_mode": self.vars["display_mode"].get().lower(),
            "refresh_rate": str(refresh),
            "vsync": "1" if self.vars["vsync"].get() else "0",
            "fps_limit": "0" if fps == "Unlimited" else fps,
            "render_resolution": self.vars["render_resolution"].get(),
            "upscaler": self.vars["upscaler"].get(),
            "preset": self.vars["preset"].get(),
            "output_res": self.vars["output_res"].get(),
            "rcas": "1" if self.vars["rcas"].get() else "0",
            "rcas_strength": str(strength),
            "fxaa": "1" if self.vars["fxaa"].get() else "0",
            "anisotropy": "0" if aniso == "Game default" else aniso,
            "engine_fps": self.vars["engine_fps"].get(),
            "shadow_quality": self.vars["shadow_quality"].get(),
            "async_shaders": "1" if self.vars["async_shaders"].get() else "0",
            "deferred_readback": "1" if self.vars["deferred_readback"].get() else "0",
            "stale_readback": "1" if self.vars["stale_readback"].get() else "0",
        }

    def save_graphics_to_ini(self):
        try:
            ini_write_keys(self.gfx_ini_path(), self.collect_graphics())
            messagebox.showinfo("Graphics", f"Saved to {self.gfx_ini_path()}")
        except OSError as exc:
            messagebox.showwarning("Graphics", f"Cannot write ini:\n{exc}")

    def _changed(self):
        self.dirty = True
        self.lbl_dirty.configure(text="Unsaved changes - Save to keep them", fg=C["warn"])
        if "key_map" in self.vars and hasattr(self, "lbl_keymap"):
            self.lbl_keymap.configure(text=self.vars["key_map"].get() or "(none)")
        self._preview()

    def _preview(self):
        self.txt_cmd.delete("1.0", tk.END)
        if self.profile is None:
            return
        backend = self.vars["backend_dir"].get()
        runner = self.vars["runner"].get()
        runner_path = Path(runner)
        if not runner_path.is_absolute() and backend:
            runner_path = Path(backend) / runner
        self.txt_cmd.insert(tk.END, "Play command\n", "key")
        self.txt_cmd.insert(tk.END, subprocess.list2cmdline([find_python(), str(runner_path)]) + "\n\n")
        self.txt_cmd.insert(tk.END, "Working directory\n", "key")
        self.txt_cmd.insert(tk.END, (backend or "(not set)") + "\n\n")
        self.txt_cmd.insert(tk.END, "Environment added or changed\n", "key")
        env = self._build_env()
        if env:
            for k in sorted(env):
                self.txt_cmd.insert(tk.END, f"  {k}={env[k]}\n")
        else:
            self.txt_cmd.insert(tk.END, "  (none)\n", "dim")
        if self.dirty:
            self.txt_cmd.insert(tk.END, "\nUnsaved settings shown; Play uses them only after Save.\n", "warn")

    def _reload_profiles(self, select=None):
        self.profiles = load_profiles()
        titles = [p["title"] for p in self.profiles]
        self.cmb["values"] = titles
        if select and select in titles:
            self.var_profile.set(select)
        if self.var_profile.get() not in titles:
            self.var_profile.set(titles[0] if titles else "")
        self._refresh_profile()

    def _refresh_profile(self):
        title = self.var_profile.get()
        self.profile = next((p for p in self.profiles if p["title"] == title), None)
        if self.profile is None:
            self.lbl_state.config(text="no game added - press Add", foreground=C["warn"])
            return
        self._fill_settings()
        self.lbl_state.config(text="ready | %s" % self.profile["title"], foreground=C["good"])
        self._preview()

    def _auto_add(self, out):
        out = Path(out)
        title, tid, ok = dump_info(out)
        if tid and out.name != tid:
            new = out.parent / tid
            if not new.exists():
                try:
                    out.rename(new)
                    out = new
                except OSError:
                    pass
        name = title or out.name
        data = {
            "name": name,
            "backend_dir": "backend",
            "runner": "run.py",
            "game_dir": str(out),
            "env": {"GOW3_SAVE_BACKUP": "0"},
            "args": [],
        }
        write_profile(PROFILES_DIR / (slug(name) + ".json"), data)
        self._reload_profiles(select=name)

    def do_add_game(self):
        win = tk.Toplevel(self.root)
        win.title("Add game")
        win.configure(bg=C["bg"])
        win.transient(self.root)
        win.resizable(False, False)

        win.update_idletasks()
        pw, ph = self.root.winfo_width(), self.root.winfo_height()
        px, py = self.root.winfo_x(), self.root.winfo_y()
        ww, wh = 560, 240
        win.geometry(f"{ww}x{wh}+{px + (pw - ww) // 2}+{py + (ph - wh) // 2}")
        win.grab_set()

        lbl = dict(bg=C["bg"], fg=C["ink"], font=UI, anchor="w")
        ent = dict(bg=C["field"], fg=C["ink"], insertbackground=C["accent"],
                   relief=tk.FLAT, highlightthickness=1,
                   highlightbackground=C["line"], highlightcolor=C["accent"],
                   font=MONO, width=40)

        tk.Label(win, text="Game name", **lbl).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 4))
        v_name = tk.StringVar(win)
        tk.Entry(win, textvariable=v_name, **ent).grid(row=0, column=1, columnspan=2, sticky="ew", padx=(8, 14), pady=(14, 4))

        tk.Label(win, text="Game directory", **lbl).grid(row=1, column=0, sticky="w", padx=14, pady=4)
        v_dir = tk.StringVar(win)
        tk.Entry(win, textvariable=v_dir, **ent).grid(row=1, column=1, sticky="ew", padx=(8, 6), pady=4)

        v_info = tk.StringVar(win, value="")
        tk.Label(win, textvariable=v_info, bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 8), anchor="w").grid(row=2, column=1, columnspan=2, sticky="w", padx=8)

        def probe(*_):
            g = v_dir.get().strip()
            if not g:
                v_info.set("")
                return
            title, tid, ok = dump_info(g)
            if ok:
                v_info.set("%s  [%s]  dump ok" % (title or "(no title)", tid or "?"))
                if title and not v_name.get().strip():
                    v_name.set(title)
            else:
                v_info.set("not a valid dump (need sce_sys/param.sfo + eboot.bin)")
        v_dir.trace_add("write", probe)

        def browse():
            p = filedialog.askdirectory(title="Select the extracted game dump folder", parent=win)
            if p:
                v_dir.set(p)
        button(win, "Browse", browse, "ghost").grid(row=1, column=2, padx=(0, 14), pady=4)

        v_backup = tk.BooleanVar(win, value=False)
        tk.Checkbutton(win, text="Back up saves before each run", variable=v_backup,
                       bg=C["bg"], fg=C["ink"], selectcolor=C["field"],
                       activebackground=C["bg"], activeforeground=C["ink"],
                       relief=tk.FLAT, highlightthickness=0, font=UI, cursor="hand2"
                       ).grid(row=3, column=1, columnspan=2, sticky="w", padx=14, pady=4)

        def ok():
            name = v_name.get().strip()
            gd = v_dir.get().strip()
            if not gd:
                messagebox.showwarning("Add game", "Game directory is required.", parent=win)
                return
            title, tid, okdump = dump_info(gd)
            if not name:
                name = title or Path(gd).name
            if not okdump:
                if not messagebox.askyesno("Add game", "Folder does not look like a valid dump. Add anyway?", parent=win):
                    return
            data = {
                "name": name,
                "backend_dir": "backend",
                "runner": "run.py",
                "game_dir": gd,
                "env": {"GOW3_SAVE_BACKUP": "1" if v_backup.get() else "0"},
                "args": [],
            }
            write_profile(PROFILES_DIR / (slug(name) + ".json"), data)
            win.destroy()
            self._reload_profiles(select=name)

        button(win, "Add", ok, "primary").grid(row=4, column=1, columnspan=2, sticky="e", padx=14, pady=(4, 14))
        win.columnconfigure(1, weight=1)

    def do_remove_game(self):
        if self.profile is None:
            return
        if not messagebox.askyesno("Remove game",
                                   f"Delete profile '{self.profile['title']}'?\nThe JSON file is removed; the game dump is untouched."):
            return
        delete_profile(self.profile["path"])
        self._reload_profiles()

    def do_install_pkg(self):
        from extract_pkg import ExtractApp
        win = tk.Toplevel(self.root)
        ExtractApp(win, on_done=self._auto_add)
        win.update_idletasks()
        pw, ph = self.root.winfo_width(), self.root.winfo_height()
        px, py = self.root.winfo_x(), self.root.winfo_y()
        ww, wh = 760, 520
        win.geometry(f"{ww}x{wh}+{px + (pw - ww) // 2}+{py + (ph - wh) // 2}")

    def _fill_settings(self):
        s = self.profile["data"] if self.profile else {}
        for key in ("backend_dir", "runner", "game_dir", "log_file"):
            self.vars[key].set(s.get(key, ""))
        self.vars["runner"].set(s.get("runner", "run.py"))
        env = s.get("env", "")
        self.vars["env"].delete("1.0", tk.END)
        self.vars["env"].insert("1.0", env if isinstance(env, str) else "")
        c = s.get("controls", {})
        self.vars["confirm"].set(c.get("confirm", "Circle"))
        self.vars["input"].set(c.get("input", "Auto"))
        self.vars["mouse_look"].set(c.get("mouse_look", "1") != "0")
        self.vars["mouse_sens"].set(c.get("mouse_sens", "1.0"))
        self.vars["mouse_invert_y"].set(c.get("mouse_invert_y", "0") == "1")
        self.vars["gyro_sens"].set(c.get("gyro_sens", "1.4"))
        self.vars["pad_map"].set(c.get("pad_map", ""))
        self.vars["key_map"].set(c.get("key_map", ""))
        self.dirty = False
        self.lbl_dirty.configure(text="All changes saved", fg=C["dim"])
        self.load_graphics_from_ini()

    def save_settings(self):
        if not self.profile:
            return
        env_dict = {}
        for line in self.vars["env"].get("1.0", "end-1c").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env_dict[k.strip()] = v.strip().strip('"')
        data = {
            "name": self.profile["title"],
            "backend_dir": self.vars["backend_dir"].get(),
            "runner": self.vars["runner"].get(),
            "game_dir": self.vars["game_dir"].get(),
            "env": env_dict,
            "log_file": self.vars["log_file"].get(),
            "controls": {
                "confirm": self.vars["confirm"].get(),
                "input": self.vars["input"].get(),
                "mouse_look": "1" if self.vars["mouse_look"].get() else "0",
                "mouse_sens": self.vars["mouse_sens"].get(),
                "mouse_invert_y": "1" if self.vars["mouse_invert_y"].get() else "0",
                "gyro_sens": self.vars["gyro_sens"].get(),
                "pad_map": self.vars["pad_map"].get(),
                "key_map": self.vars["key_map"].get(),
            },
        }
        try:
            write_profile(self.profile["path"], data)
            self.profile["data"] = data
            self.dirty = False
            self.lbl_dirty.configure(text="Saved - applies on next start", fg=C["good"])
        except Exception as exc:
            messagebox.showerror("Save", str(exc))

    def revert_settings(self):
        self._fill_settings()

    def _build_env(self):
        env = {}
        game = self.vars["game_dir"].get()
        if game:
            env["GOW3_GAME_DIR"] = game
        env["GOW3_MENU_CONFIRM"] = self.vars["confirm"].get().lower()
        mode = self.vars["input"].get()
        if mode in ("Pad", "Keyboard"):
            env["GOW3_INPUT"] = mode.lower()
        env["GOW3_MOUSE_LOOK"] = "1" if self.vars["mouse_look"].get() else "0"
        env["GOW3_MOUSE_INVERT_Y"] = "1" if self.vars["mouse_invert_y"].get() else "0"
        if self.vars["mouse_sens"].get():
            env["GOW3_MOUSE_SENS"] = self.vars["mouse_sens"].get()
        if self.vars["gyro_sens"].get():
            env["GOW3_GYRO_SENS"] = self.vars["gyro_sens"].get()
        if self.vars["pad_map"].get():
            env["GOW3_PAD_MAP"] = self.vars["pad_map"].get()
        if self.vars["key_map"].get():
            env["GOW3_KEY_MAP"] = self.vars["key_map"].get()
        for line in self.vars["env"].get("1.0", "end-1c").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"')
        return env

    def _set_busy(self, busy, play=False):
        self.busy = busy
        self.btn_play.configure(state=tk.DISABLED if busy else tk.NORMAL)
        self.btn_stop.configure(state=tk.NORMAL if (busy and play) else tk.DISABLED)
        if busy:
            self.lbl_state.config(text="running", foreground=C["warn"])

    def do_play(self):
        if self.busy or self.profile is None:
            return
        if self.dirty:
            a = messagebox.askyesnocancel("Unsaved settings",
                                          "Save before starting?\nYes = save and play, No = play with saved profile.")
            if a is None:
                return
            if a:
                self.save_settings()

        backend = self.vars["backend_dir"].get()
        runner = self.vars["runner"].get()
        if not backend:
            messagebox.showerror("Play", "Backend directory is empty.")
            return
        backend_path = Path(backend)
        if not backend_path.is_absolute():
            backend_path = ROOT / backend_path
        if not backend_path.is_dir():
            messagebox.showerror("Play", f"Backend directory does not exist:\n{backend}")
            return
        runner_path = Path(runner)
        if not runner_path.is_absolute():
            runner_path = backend_path / runner
        runner_path = runner_path.resolve(strict=False)
        if not runner_path.is_file():
            messagebox.showerror("Play", f"Runner does not exist:\n{runner_path}")
            return

        log_input = self.vars["log_file"].get() or f"logs/launch-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
        log_path = Path(log_input)
        if not log_path.is_absolute():
            log_path = ROOT / log_path
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Play", f"Cannot create log directory:\n{exc}")
            return

        try:
            ini_write_keys(self.gfx_ini_path(), self.collect_graphics())
        except OSError:
            pass

        env = os.environ.copy()
        env.update(self._build_env())
        game = self.vars["game_dir"].get()
        if game:
            icon = self._resolve_window_icon(game)
            if icon is not None:
                env["GOW3_WINDOW_ICON"] = icon
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        command = [find_python(), str(runner_path)]
        try:
            self.gp.start(command, backend_path, env, log_path)
        except Exception as exc:
            messagebox.showerror("Play", f"Failed to start:\n{exc}")
            return

        self._stop_requested = False
        self._set_busy(True, play=True)
        self.root.after(250, self._poll)

    def _poll(self):
        rc = self.gp.poll()
        if rc is None:
            self.root.after(250, self._poll)
            return
        self.gp.cleanup()
        self._set_busy(False)
        if self._stop_requested:
            self._stop_requested = False
            self.lbl_state.config(text="stopped", foreground=C["muted"])
            return
        if rc == 0:
            self.lbl_state.config(text="finished", foreground=C["good"])
            return
        self.lbl_state.config(text="exit code %s" % rc, foreground=C["warn"])
        self.do_open_logs()

    def do_stop(self):
        if not self.gp.running:
            return
        if not messagebox.askyesno("Stop", "Kill the game process?\nThe last seconds of a save can be lost.\nClosing the game window is safer."):
            return
        self._stop_requested = True
        self.gp.stop()
        if self.gp.process is not None:
            try:
                kill_process_tree(self.gp.process.pid)
            except Exception:
                pass
        self.lbl_state.config(text="stopping", foreground=C["warn"])

    def do_open_logs(self):
        d = ROOT / "logs"
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        if not d.is_dir():
            messagebox.showinfo("Logs", "No logs folder yet.")
            return
        try:
            os.startfile(str(d))
        except Exception as exc:
            messagebox.showerror("Logs", str(exc))

    def _close(self):
        if self.gp.running:
            if not messagebox.askyesno("Quit", "The game is running. Stop it and quit?"):
                return
            self._stop_requested = True
            self.gp.stop()
            self.gp.cleanup()
        if self.dirty and not messagebox.askyesno("Quit", "Settings are not saved. Quit anyway?"):
            return
        self._save_geometry()
        self.root.destroy()


def main():
    global _MUTEX
    if sys.platform == "win32":
        k = ctypes.windll.kernel32
        _MUTEX = k.CreateMutexW(None, False, "JollyBaron.PS4Recomp.SingleInstance")
        if k.GetLastError() == 183:
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror("JB PS4Recomp", "Launcher is already running.")
            r.destroy()
            sys.exit(0)
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
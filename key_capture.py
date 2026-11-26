# JB PS4Recomp - keyboard/mouse button capture.
# Copyright (c) 2026 Jolly Baron.
# SPDX-License-Identifier: GPL-2.0-or-later
"""Capture a keyboard/mouse mapping into GOW3_KEY_MAP tokens.

The parser (runtime_pad.c apply_button_map, keyboard=true) splits ',' '=' '|',
compares case-insensitively (SDL_strcasecmp), and resolves the right-hand side
via SDL_GetScancodeFromName or the mouse_names table. This module emits exactly
those tokens, so the captured string is guaranteed parseable.

Gamepad capture is NOT here: SDL gamepad button string names are ambiguous and
the pad-side parser is unconfirmed; edit the raw Pad map in Debug for now.
"""
import tkinter as tk
from tkinter import ttk

from theme import C, MONO, UI, apply_theme, button, Scroll

PS_BUTTONS = [
    ("cross", "Cross"), ("circle", "Circle"), ("square", "Square"),
    ("triangle", "Triangle"), ("l1", "L1"), ("r1", "R1"),
    ("l2", "L2"), ("r2", "R2"), ("l3", "L3"), ("r3", "R3"),
    ("options", "Options (Start)"), ("up", "D-pad Up"), ("down", "D-pad Down"),
    ("left", "D-pad Left"), ("right", "D-pad Right"),
    ("touchpad", "Touchpad (Select)"),
]

KEYSYM_TO_SDL = {
    **{c: c.upper() for c in "abcdefghijklmnopqrstuvwxyz"},
    **{str(d): str(d) for d in range(10)},
    "space": "Space", "Return": "Return", "Escape": "Escape", "Tab": "Tab",
    "BackSpace": "Backspace", "Delete": "Delete", "Insert": "Insert",
    "Home": "Home", "End": "End", "Prior": "PageUp", "Next": "PageDown",
    "Up": "Up", "Down": "Down", "Left": "Left", "Right": "Right",
    "Shift_L": "LShift", "Shift_R": "RShift",
    "Control_L": "LCtrl", "Control_R": "RCtrl",
    "Alt_L": "LAlt", "Alt_R": "RAlt",
    "grave": "Grave", "minus": "Minus", "equal": "Equals",
    "bracketleft": "LeftBracket", "bracketright": "RightBracket",
    "backslash": "Backslash", "semicolon": "Semicolon", "apostrophe": "Apostrophe",
    "comma": "Comma", "period": "Period", "slash": "Slash",
    "Caps_Lock": "CapsLock", "Num_Lock": "Numlock", "Scroll_Lock": "ScrollLock",
    "Print": "PrintScreen", "Pause": "Pause",
    **{f"F{n}": f"F{n}" for n in range(1, 13)},
    **{f"KP_{d}": f"KP_{d}" for d in range(10)},
    "KP_Enter": "KP_Enter", "KP_Add": "KP_Plus", "KP_Subtract": "KP_Minus",
    "KP_Multiply": "KP_Multiply", "KP_Divide": "KP_Divide",
    "KP_Decimal": "KP_Period", "KP_Separator": "KP_Period",
}

MOUSE_TO_SDL = {1: "Mouse Left", 2: "Mouse Middle", 3: "Mouse Right"}


def _token(event):
    keysym = event.keysym
    if keysym in KEYSYM_TO_SDL:
        return KEYSYM_TO_SDL[keysym]
    if event.num in MOUSE_TO_SDL:
        return MOUSE_TO_SDL[event.num]
    return "Unknown:" + (keysym or ("Button%d" % event.num))


def _current_token(vars_dict, ps):
    cur = vars_dict["key_map"].get()
    for chunk in cur.split(","):
        if "=" not in chunk:
            continue
        k, val = chunk.split("=", 1)
        if k.strip().lower() == ps:
            return val.strip()
    return ""


def capture_mapping(root, vars_dict, on_change):
    win = tk.Toplevel(root)
    win.title("Capture mapping (keyboard / mouse)")
    win.configure(bg=C["bg"])
    win.transient(root)
    win.grab_set()
    win.update_idletasks()
    pw, ph = root.winfo_width(), root.winfo_height()
    px, py = root.winfo_x(), root.winfo_y()
    ww, wh = 560, 640
    win.geometry(f"{ww}x{wh}+{px + (pw - ww) // 2}+{py + (ph - wh) // 2}")
    win.minsize(480, 420)

    head = ttk.Frame(win, padding=(14, 12, 14, 4))
    head.pack(fill=tk.X)
    ttk.Label(head, text="Press a key or mouse button after Capture.",
              style="Hint.TLabel").pack(anchor="w")
    ttk.Label(head, text="Gamepad is not captured here (see Debug).",
              style="Hint.TLabel").pack(anchor="w")

    # scrollable rows so Save is always reachable
    sc = Scroll(win)
    sc.pack(fill=tk.BOTH, expand=True, padx=14, pady=4)
    body = sc.body
    rows = {}
    for ps, label in PS_BUTTONS:
        r = ttk.Frame(body, style="Panel.TFrame")
        r.pack(fill=tk.X, pady=2)
        ttk.Label(r, text=label, width=16, style="Panel.TLabel").pack(side=tk.LEFT)
        v = tk.StringVar(value=_current_token(vars_dict, ps))
        e = tk.Entry(r, textvariable=v, width=22, bg=C["field"], fg=C["ink"],
                     insertbackground=C["accent"], relief=tk.FLAT, highlightthickness=1,
                     highlightbackground=C["line"], highlightcolor=C["accent"], font=MONO)
        e.pack(side=tk.LEFT, padx=6)
        cap = {"row": None}

        def _mk(var, capref):
            def do_cap():
                capref["row"] = (var,)
            return do_cap
        button(r, "Capture", _mk(v, cap), "ghost").pack(side=tk.LEFT)
        rows[ps] = (v, cap)

    def on_event(event):
        target = None
        for ps, (v, cap) in rows.items():
            if cap["row"] is not None:
                target = (v, cap)
                break
        if target is None:
            return
        var, cap = target
        var.set(_token(event))
        cap["row"] = None

    win.bind_all("<KeyPress>", on_event)
    win.bind_all("<Button-1>", on_event)
    win.bind_all("<Button-2>", on_event)
    win.bind_all("<Button-3>", on_event)

    foot = ttk.Frame(win, padding=(14, 4, 14, 12))
    foot.pack(fill=tk.X)

    def _unbind():
        win.unbind_all("<KeyPress>")
        win.unbind_all("<Button-1>")
        win.unbind_all("<Button-2>")
        win.unbind_all("<Button-3>")

    def save():
        parts = []
        for ps, _label in PS_BUTTONS:
            v, _cap = rows[ps]
            tok = v.get().strip()
            if tok and not tok.startswith("Unknown:"):
                parts.append("%s=%s" % (ps, tok))
        vars_dict["key_map"].set(",".join(parts))
        _unbind()
        win.destroy()
        on_change()

    def cancel():
        _unbind()
        win.destroy()

    button(foot, "Save", save, "primary").pack(side=tk.LEFT, padx=4)
    button(foot, "Cancel", cancel, "ghost").pack(side=tk.LEFT, padx=4)
    win.protocol("WM_DELETE_WINDOW", cancel)
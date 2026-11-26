# JB PS4Recomp - theme and widget primitives.
# Copyright (c) 2026 Jolly Baron.
# SPDX-License-Identifier: GPL-2.0-or-later
"""JB PS4Recomp - theme and widget primitives."""
import tkinter as tk
from tkinter import ttk

C = {
    "bg": "#0e1116", "panel": "#151a21", "field": "#0a0d12", "raise": "#1c232c",
    "line": "#26303b", "select": "#22303f", "ink": "#dfe4ea", "muted": "#8a939f",
    "dim": "#5d6672", "accent": "#4aa3ff", "gold": "#c9a227", "good": "#6fdc8c",
    "warn": "#f0b429", "bad": "#ff6b6b", "on_accent": "#06121f",
}

MONO = ("Consolas", 9)
MONO_BIG = ("Consolas", 10)
UI = ("Segoe UI", 9)
UI_B = ("Segoe UI", 9, "bold")
TITLE = ("Segoe UI", 15, "bold")


def apply_theme(root):
    root.configure(bg=C["bg"])
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass

    st.configure(".", background=C["bg"], foreground=C["ink"], font=UI,
                 bordercolor=C["line"], lightcolor=C["panel"], darkcolor=C["panel"])
    st.configure("TFrame", background=C["bg"])
    st.configure("Panel.TFrame", background=C["panel"])
    st.configure("TLabel", background=C["bg"], foreground=C["ink"])
    st.configure("Panel.TLabel", background=C["panel"], foreground=C["ink"])
    st.configure("Muted.TLabel", background=C["bg"], foreground=C["muted"])
    st.configure("Hint.TLabel", background=C["panel"], foreground=C["dim"], font=("Segoe UI", 8))
    st.configure("Head.TLabel", background=C["panel"], foreground=C["accent"], font=UI_B)
    st.configure("Gold.TLabel", background=C["panel"], foreground=C["gold"], font=UI_B)
    st.configure("Title.TLabel", background=C["bg"], foreground=C["ink"], font=TITLE)
    st.configure("Brand.TLabel", background=C["bg"], foreground=C["gold"], font=("Segoe UI", 8, "bold"))

    st.configure("TCheckbutton", background=C["panel"], foreground=C["ink"],
                 bordercolor=C["line"], focusthickness=0)
    st.map("TCheckbutton", background=[("active", C["panel"])],
           foreground=[("disabled", C["dim"])],
           indicatorcolor=[("selected", C["accent"]), ("!selected", C["field"])])

    st.configure("TCombobox", fieldbackground=C["field"], background=C["raise"],
                 foreground=C["ink"], arrowcolor=C["accent"], bordercolor=C["line"],
                 insertcolor=C["ink"], padding=4)
    st.map("TCombobox", fieldbackground=[("readonly", C["field"])],
           foreground=[("readonly", C["ink"])], bordercolor=[("focus", C["accent"])])
    root.option_add("*TCombobox*Listbox.background", C["field"])
    root.option_add("*TCombobox*Listbox.foreground", C["ink"])
    root.option_add("*TCombobox*Listbox.selectBackground", C["select"])
    root.option_add("*TCombobox*Listbox.selectForeground", C["ink"])
    root.option_add("*TCombobox*Listbox.borderWidth", 0)

    st.configure("TEntry", fieldbackground=C["field"], foreground=C["ink"],
                 insertcolor=C["accent"], bordercolor=C["line"], padding=4)
    st.map("TEntry", bordercolor=[("focus", C["accent"])])

    st.configure("TNotebook", background=C["bg"], bordercolor=C["line"], tabmargins=(8, 8, 8, 0))
    st.configure("TNotebook.Tab", background=C["bg"], foreground=C["muted"],
                 padding=(16, 8), bordercolor=C["line"], font=UI)
    st.map("TNotebook.Tab", background=[("selected", C["panel"])],
           foreground=[("selected", C["accent"])])

    st.configure("TScrollbar", background=C["raise"], troughcolor=C["field"],
                 bordercolor=C["line"], arrowcolor=C["muted"], width=12)
    st.map("TScrollbar", background=[("active", C["accent"])])
    st.configure("TSeparator", background=C["line"])


def dark_text(w, big=False):
    w.configure(bg=C["field"], fg=C["ink"], insertbackground=C["accent"],
                selectbackground=C["select"], selectforeground=C["ink"],
                relief=tk.FLAT, borderwidth=0, highlightthickness=1,
                highlightbackground=C["line"], highlightcolor=C["accent"],
                font=MONO_BIG if big else MONO, padx=10, pady=8)


def button(parent, text, command, kind="normal", width=None):
    pal = {
        "normal": (C["raise"], C["ink"], C["select"]),
        "primary": (C["accent"], C["on_accent"], "#6cb6ff"),
        "danger": (C["raise"], C["bad"], "#3a2226"),
        "ghost": (C["panel"], C["muted"], C["raise"]),
    }[kind]
    b = tk.Button(parent, text=text, command=command,
                  bg=pal[0], fg=pal[1], activebackground=pal[2], activeforeground=pal[1],
                  relief=tk.FLAT, borderwidth=0, highlightthickness=0,
                  padx=14, pady=6, font=UI_B if kind == "primary" else UI,
                  cursor="hand2", disabledforeground=C["dim"])
    if width:
        b.configure(width=width)
    b.bind("<Enter>", lambda e: b.configure(bg=pal[2]) if b["state"] != "disabled" else None)
    b.bind("<Leave>", lambda e: b.configure(bg=pal[0]))
    return b


def segmented(parent, var, choices, on_change):
    holder = tk.Frame(parent, bg=C["panel"])
    buttons = []

    def paint(*_):
        try:
            current = var.get()
        except Exception:
            current = None
        for widget, value in buttons:
            if value == current:
                widget.configure(bg=C["accent"], fg=C["on_accent"],
                                 activebackground=C["accent"], activeforeground=C["on_accent"])
            else:
                widget.configure(bg=C["field"], fg=C["muted"],
                                 activebackground=C["select"], activeforeground=C["ink"])

    for text, value in choices:
        b = tk.Radiobutton(holder, text=text, value=value, variable=var,
                           indicatoron=False, relief=tk.FLAT, borderwidth=0,
                           highlightthickness=0, padx=16, pady=6,
                           font=UI_B, cursor="hand2", command=on_change)
        b.pack(side=tk.LEFT, padx=2)
        buttons.append((b, value))

    var.trace_add("write", paint)
    paint()
    return holder


class Scroll(tk.Frame):
    def __init__(self, parent, bg=None):
        bg = bg or C["bg"]
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, borderwidth=0)
        self.bar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.body = tk.Frame(self.canvas, bg=bg)
        self.win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.body.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.win, width=e.width))
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.bind_all(seq, self._wheel, add="+")

    def _wheel(self, event):
        if not self.winfo_exists():
            return
        try:
            x, y = self.winfo_pointerxy()
            w = self.winfo_containing(x, y)
        except Exception:
            return
        node = w
        while node is not None:
            if node is self:
                break
            node = getattr(node, "master", None)
        if node is not self:
            return
        if event.num == 4:
            self.canvas.yview_scroll(-3, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(3, "units")
        else:
            self.canvas.yview_scroll(int(-event.delta / 40), "units")
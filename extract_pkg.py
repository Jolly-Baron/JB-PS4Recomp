# JB PS4Recomp - standalone PKG extractor.
# Copyright (c) 2026 Jolly Baron.
# SPDX-License-Identifier: GPL-2.0-or-later
"""JB PS4Recomp - extract a PS4 .pkg into a playable folder.

GUI:  python extract_pkg.py
CLI:  python extract_pkg.py game.pkg out_dir
Uses the backend's own pkg_extract; no extra dependencies.
"""
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND / "scripts"))
sys.path.insert(0, str(ROOT))

from theme import C, MONO, UI, UI_B, apply_theme, dark_text, button


def run_extract(pkg, out, report):
    import pkg_extract
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pkg_extract.extract(Path(pkg), out, report)
    return out


class ExtractApp:
    def __init__(self, root, on_done=None):
        self.root = root
        self.on_done = on_done
        root.title("JB PS4Recomp - Extract PKG")
        root.geometry("760x520")
        root.minsize(640, 420)
        apply_theme(root)
        st = ttk.Style(root)
        st.configure("Horizontal.TProgressbar", background=C["accent"],
                     troughcolor=C["field"], bordercolor=C["line"],
                     lightcolor=C["accent"], darkcolor=C["accent"])
        self.q = queue.Queue()
        self.busy = False

        wrap = ttk.Frame(root, padding=14)
        wrap.pack(fill=tk.BOTH, expand=True)
        wrap.columnconfigure(1, weight=1)

        ttk.Label(wrap, text="PKG file").grid(row=0, column=0, sticky="w", pady=4)
        self.v_pkg = tk.StringVar()
        tk.Entry(wrap, textvariable=self.v_pkg, bg=C["field"], fg=C["ink"],
                 insertbackground=C["accent"], relief=tk.FLAT, highlightthickness=1,
                 highlightbackground=C["line"], highlightcolor=C["accent"],
                 font=MONO).grid(row=0, column=1, sticky="ew", padx=6, pady=4)
        button(wrap, "Browse", self._browse_pkg, "ghost").grid(row=0, column=2, pady=4)

        ttk.Label(wrap, text="Output folder").grid(row=1, column=0, sticky="w", pady=4)
        self.v_out = tk.StringVar(value=str(ROOT / "games"))
        tk.Entry(wrap, textvariable=self.v_out, bg=C["field"], fg=C["ink"],
                 insertbackground=C["accent"], relief=tk.FLAT, highlightthickness=1,
                 highlightbackground=C["line"], highlightcolor=C["accent"],
                 font=MONO).grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        button(wrap, "Browse", self._browse_out, "ghost").grid(row=1, column=2, pady=4)

        bar = ttk.Frame(wrap)
        bar.grid(row=2, column=0, columnspan=3, sticky="ew", pady=8)
        self.btn = button(bar, "Extract", self.do_extract, "primary")
        self.btn.pack(side=tk.LEFT)
        self.prog = ttk.Progressbar(bar, orient=tk.HORIZONTAL, mode="determinate")
        self.prog.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.lbl = ttk.Label(bar, text="idle", foreground=C["muted"])
        self.lbl.pack(side=tk.LEFT)

        self.log = tk.Text(wrap, wrap=tk.NONE, height=14)
        dark_text(self.log)
        self.log.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=6)
        wrap.rowconfigure(3, weight=1)
        sb = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        sb.grid(row=3, column=3, sticky="ns")

        ttk.Label(wrap, text="After extraction the launcher adds the game automatically.",
                  foreground=C["dim"], font=("Segoe UI", 8)).grid(row=4, column=0, columnspan=3, sticky="w")
        root.after(100, self._drain)

    def _browse_pkg(self):
        p = filedialog.askopenfilename(title="Select PS4 .pkg",
                                       filetypes=[("PS4 package", "*.pkg"), ("All files", "*.*")])
        if p:
            self.v_pkg.set(p)
            stem = Path(p).stem
            self.v_out.set(str(ROOT / "games" / stem))

    def _browse_out(self):
        p = filedialog.askdirectory(title="Select output folder")
        if p:
            self.v_out.set(p)

    def _log(self, line):
        self.log.insert(tk.END, line + "\n")
        self.log.see(tk.END)

    def do_extract(self):
        if self.busy:
            return
        pkg = self.v_pkg.get().strip()
        out = self.v_out.get().strip()
        if not pkg or not Path(pkg).is_file():
            messagebox.showerror("Extract", "Select a .pkg file.", parent=self.root)
            return
        if not out:
            messagebox.showerror("Extract", "Select an output folder.", parent=self.root)
            return
        self.busy = True
        self.btn.configure(state=tk.DISABLED)
        self.prog.configure(value=0, maximum=100)
        self.lbl.configure(text="working", foreground=C["warn"])
        self._log("$ extract %s -> %s" % (pkg, out))

        def report(done, total, rate):
            self.q.put(("prog", (done, total, rate)))

        def work():
            try:
                run_extract(pkg, out, report)
                self.q.put(("done", out))
            except Exception as exc:
                self.q.put(("err", "%s: %s" % (type(exc).__name__, exc)))

        threading.Thread(target=work, daemon=True).start()

    def _drain(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "prog":
                    done, total, rate = payload
                    if total:
                        self.prog.configure(maximum=total, value=done)
                    self.lbl.configure(text="%d/%d" % (done, total or 0), foreground=C["muted"])
                elif kind == "done":
                    self.busy = False
                    self.btn.configure(state=tk.NORMAL)
                    self.lbl.configure(text="done", foreground=C["good"])
                    self._log("extracted -> %s" % payload)
                    if self.on_done:
                        self.on_done(payload)
                elif kind == "err":
                    self.busy = False
                    self.btn.configure(state=tk.NORMAL)
                    self.lbl.configure(text="failed", foreground=C["bad"])
                    self._log("ERROR %s" % payload)
        except queue.Empty:
            pass
        try:
            if self.root.winfo_exists():
                self.root.after(100, self._drain)
        except tk.TclError:
            pass


def main():
    if len(sys.argv) >= 3:
        pkg, out = sys.argv[1], sys.argv[2]
        def report(done, total, rate):
            if total:
                sys.stdout.write("\r%d/%d" % (done, total))
                sys.stdout.flush()
        run_extract(pkg, out, report)
        print("\nextracted -> %s" % out)
        return
    root = tk.Tk()
    ExtractApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
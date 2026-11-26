# JB PS4Recomp - paths, process control, profiles, ini.
# Copyright (c) 2026 Jolly Baron.
# SPDX-License-Identifier: GPL-2.0-or-later
"""JB PS4Recomp - paths, process control, profiles, ini."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROFILES_DIR = ROOT / "profiles"
LOGS_DIR = ROOT / "logs"
LOGO_PATH = ROOT / "assets" / "logo.png"
ICON_PATH = ROOT / "assets" / "icon.png"

IS_WINDOWS = sys.platform == "win32"

if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).resolve().parent
else:
    ROOT = Path(__file__).resolve().parent

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class _JobLimits(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", ctypes.c_uint32),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", ctypes.c_uint32),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", ctypes.c_uint32),
            ("SchedulingClass", ctypes.c_uint32),
        ]

    _KILL_ON_CLOSE = 0x00002000
    _JobBasicLimitInfo = 2
    CREATE_UNICODE_ENVIRONMENT = 0x00000400

    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.TerminateJobObject.restype = wintypes.BOOL
    kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def find_python():
    """Interpreter for backend/run.py. Dev mode: this very python. Frozen mode:
    bundled python/ next to the exe, else system python, else a clear error.
    A frozen launcher must never spawn itself as the interpreter."""
    if getattr(sys, "frozen", False):
        emb = ROOT / "python" / ("python.exe" if IS_WINDOWS else "python")
        if emb.is_file():
            return str(emb)
        found = shutil.which("python")
        if found:
            return found
        raise RuntimeError(
            "No Python interpreter found. Ship python/ next to the launcher "
            "or install Python system-wide."
        )
    exe = Path(sys.executable)
    if exe.name.lower() in ("pythonw.exe", "pythonw"):
        exe = exe.with_name("python.exe")
    return str(exe)


def _create_job():
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise OSError(f"CreateJobObjectW failed: {ctypes.get_last_error()}")
    basic = _JobLimits()
    basic.LimitFlags = _KILL_ON_CLOSE
    kernel32.SetInformationJobObject(job, _JobBasicLimitInfo,
                                     ctypes.addressof(basic), ctypes.sizeof(basic))
    return job


def _assign_job(job, handle):
    return bool(kernel32.AssignProcessToJobObject(job, wintypes.HANDLE(handle)))


def _close_job(job):
    if job:
        kernel32.CloseHandle(job)


def kill_process_tree(pid):
    if IS_WINDOWS:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)],
                       creationflags=subprocess.CREATE_NO_WINDOW,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        try:
            os.kill(pid, 15)
        except Exception:
            pass


class GameProcess:
    """Owns the child tree: Popen + optional Windows Job Object + the log file."""

    def __init__(self):
        self.process = None
        self.job = None
        self.log_handle = None
        self.current_log = ""

    @property
    def running(self):
        return self.process is not None and self.process.poll() is None

    def start(self, command, cwd, env, log_path):
        self.log_handle = open(log_path, "w", encoding="utf-8", errors="replace", newline="\n")
        flags = 0
        if IS_WINDOWS:
            flags = subprocess.CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT
        self.process = subprocess.Popen(
            command, cwd=str(cwd), stdin=subprocess.DEVNULL,
            stdout=self.log_handle, stderr=subprocess.STDOUT,
            env=env, creationflags=flags,
        )
        if IS_WINDOWS:
            try:
                self.job = _create_job()
                if not _assign_job(self.job, self.process._handle):
                    raise OSError("AssignProcessToJobObject failed")
            except Exception:
                _close_job(self.job)
                self.job = None
        self.current_log = str(log_path)

    def poll(self):
        if self.process is None:
            return None
        return self.process.poll()

    def stop(self):
        if self.process is None:
            return
        if IS_WINDOWS and self.job:
            kernel32.TerminateJobObject(self.job, 1)
        else:
            kill_process_tree(self.process.pid)

    def cleanup(self):
        self.process = None
        if self.log_handle:
            try:
                self.log_handle.close()
            except Exception:
                pass
            self.log_handle = None
        if IS_WINDOWS:
            _close_job(self.job)
        self.job = None


def ini_read(path):
    values = {}
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return values
    for line in lines:
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def ini_write_keys(path, updates):
    path = Path(path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = ["# JB PS4Recomp graphics settings"]
    done, out = set(), []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else None
        if key in updates:
            out.append(f"{key}={updates[key]}")
            done.add(key)
        else:
            out.append(line)
    out += [f"{k}={v}" for k, v in updates.items() if k not in done]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def read_tail(path, lines=200, chunk=131072):
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - chunk), os.SEEK_SET)
            data = f.read().decode("utf-8", "replace")
            return "\n".join(data.splitlines()[-lines:])
    except Exception as exc:
        return f"Cannot read log: {exc}"


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "game"


def load_profiles():
    out = []
    if not PROFILES_DIR.is_dir():
        return out
    for p in sorted(PROFILES_DIR.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            out.append({"path": p, "data": data, "title": data.get("name", p.stem)})
        except Exception:
            pass
    return out


def write_profile(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def delete_profile(path):
    Path(path).unlink(missing_ok=True)
def png_to_bmp(png_path, bmp_path, size=64):
    """Convert a PNG (game icon) to a 24-bit BMP using only Tk, no PIL.
    Returns True on success. Used for the per-game window icon."""
    import struct
    import tkinter as tk
    src = Path(png_path)
    if not src.is_file():
        return False
    try:
        img = tk.PhotoImage(file=str(src))
    except Exception:
        return False
    factor = max(1, round(max(img.width(), img.height()) / size))
    if factor > 1:
        img = img.subsample(factor, factor)
    w, h = img.width(), img.height()
    rows = []
    for y in range(h):
        row = bytearray()
        for x in range(w):
            c = img.get(x, y)
            if isinstance(c, str):
                c = c.lstrip('#')
                r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
            else:
                r, g, b = c[0], c[1], c[2]
            row += bytes((b, g, r))
        row += b'\x00' * ((-len(row)) % 4)
        rows.append(bytes(row))
    pixel = b''.join(reversed(rows))
    off = 54
    hdr = struct.pack('<2sIHHI', b'BM', off + len(pixel), 0, 0, off)
    info = struct.pack('<IiiHHIIiiII', 40, w, h, 1, 24, 0, len(pixel), 0, 0, 0, 0)
    out = Path(bmp_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(hdr + info + pixel)
    return True
def read_sfo(path):
    """Minimal PSF (param.sfo) reader: TITLE / TITLE_ID etc. Stdlib only."""
    import struct
    p = Path(path)
    if not p.is_file():
        return {}
    b = p.read_bytes()
    if len(b) < 20 or b[:4] != b'\x00PSF':
        return {}
    _ver, key_start, data_start, count = struct.unpack_from('<IIII', b, 4)
    out = {}
    for i in range(count):
        off = 20 + i * 16
        if off + 16 > len(b):
            break
        key_off, fmt, dlen, _dmax, data_off = struct.unpack_from('<HHIII', b, off)
        k = b[key_start + key_off:].split(b'\x00', 1)[0].decode('utf8', 'replace')
        raw = b[data_start + data_off:data_start + data_off + dlen]
        if fmt == 0x0204:
            out[k] = raw.split(b'\x00', 1)[0].decode('utf8', 'replace')
        elif fmt == 0x0004 and len(raw) >= 4:
            out[k] = struct.unpack_from('<I', raw, 0)[0]
        else:
            out[k] = raw
    return out
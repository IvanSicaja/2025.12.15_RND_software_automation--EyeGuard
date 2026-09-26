"""
EyeGuard Configurator
Standalone configuration GUI for EyeGuard.
Run this script (or its EXE) from the same folder as main.py / main.exe.
It reads and writes config.json in that same folder.
"""

import json
import os
import shutil
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

# ── Sound preview (pygame) ──────────────────────────────────────────
try:
    import pygame
    pygame.mixer.init()
    _PYGAME_OK = True
except Exception:
    _PYGAME_OK = False

def preview_sound(sound_path):
    """Play a sound file for preview. Non-blocking. Silently ignored if pygame unavailable."""
    if not _PYGAME_OK or not sound_path or not os.path.exists(sound_path):
        return
    def _play():
        try:
            pygame.mixer.music.load(sound_path)
            pygame.mixer.music.play()
        except Exception:
            pass
    threading.Thread(target=_play, daemon=True).start()

# ====================== PATHS ======================
SCRIPT_DIR  = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FIGURES_DIR = os.path.join(BASE_DIR, "assets", "media", "figures")
SOUNDS_DIR  = os.path.join(BASE_DIR, "assets", "media", "sounds")
ICON_PATH   = os.path.join(BASE_DIR, "assets", "media", "icons", "icon.png")

ALLOWED_IMAGE_EXTS = (".png", ".jpg", ".jpeg")
ALLOWED_SOUND_EXTS = (".mp3", ".wav")

# Sentinel labels shown as the first item in every image / sound dropdown
CUSTOM_IMAGE_LABEL = "➕  Add custom image…"
CUSTOM_SOUND_LABEL = "➕  Add custom sound…"

FIXED_TRIGGERS = ["start", "work_end"]
TRIGGER_LABELS = {
    "start":    "On Start",
    "work_end": "Work Time  ⏱  (popup fires → then wait this long)",
}

DEFAULT_CONFIG = {
    "work_time_min":  24,
    "work_time_sec":   0,
    "popup_opacity": 100,
    "test_mode":   False,
    "cycle_align":  True,
    "font_name":   "Montserrat",
    "message_color": "#222222",
    "popups": [
        {"trigger": "start",     "message": "EyeGuard is now active \u2014 helping you care for your eyes!", "image": "1.png", "sound": "sound_01.mp3", "sound_repeat": 1},
        {"trigger": "work_end",  "message": "Your eyes deserve a quick rest. Take a 30-second break!",       "image": "2.png", "sound": "sound_04.mp3", "sound_repeat": 1},
        {"trigger": "break_end", "message": "Let AI help \u2014 build, test, commit!",                        "image": "3.png", "sound": "sound_09.mp3", "sound_repeat": 1, "duration_min": 3, "duration_sec": 0},
        {"trigger": "break_end", "message": "Your eyes deserve a quick rest. Take a 60-second break!",       "image": "2.png", "sound": "sound_05.mp3", "sound_repeat": 2, "duration_min": 1, "duration_sec": 0},
        {"trigger": "break_end", "message": "You\u2019re refreshed now! Go enjoy your life!",                 "image": "1.png", "sound": "sound_10.mp3", "sound_repeat": 3, "duration_min": 2, "duration_sec": 0},
        {"trigger": "break_end", "message": "Great! Let\u2019s get back to it, refreshed and focused!",      "image": "4.png", "sound": "sound_06.mp3", "sound_repeat": 3, "duration_min": 0, "duration_sec": 0},
    ],
}

# ====================== HELPERS ======================

def load_config():
    """
    Load config.json from SCRIPT_DIR (same folder as the .exe / script).
    Falls back to DEFAULT_CONFIG if the file is missing or unreadable.
    Never calls messagebox here — Tk may not exist yet.
    Stores any load error in load_config.error so __init__ can show it after Tk starts.
    """
    load_config.error = None
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # ── Migrate old key names ──────────────────────────────────
            if "work_time" in cfg and "work_time_min" not in cfg:
                cfg["work_time_min"] = cfg.pop("work_time")
                cfg.setdefault("work_time_sec", 0)
            if "break_time" in cfg or "free_time" in cfg:
                brk_min  = cfg.pop("break_time", 3)
                free_min = cfg.pop("free_time", 2)
                for p in cfg.get("popups", []):
                    if p.get("trigger") == "break_end" and "duration_min" not in p:
                        p["duration_min"] = brk_min
                        p["duration_sec"] = 0
                for p in cfg.get("popups", []):
                    if p.get("trigger") == "free_end":
                        p["trigger"]      = "break_end"
                        p["duration_min"] = free_min
                        p["duration_sec"] = 0
            # ── Fill any missing top-level keys with defaults ──────────
            for k, v in DEFAULT_CONFIG.items():
                cfg.setdefault(k, v)
            return cfg
        except Exception as e:
            load_config.error = str(e)
    return json.loads(json.dumps(DEFAULT_CONFIG))

load_config.error = None   # initialise attribute

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        messagebox.showerror("Save Error", f"Could not write config.json:\n{e}")
        return False

def list_figures():
    """Return available images with the custom-import option first."""
    if not os.path.isdir(FIGURES_DIR):
        return [CUSTOM_IMAGE_LABEL]
    files = sorted(f for f in os.listdir(FIGURES_DIR)
                   if os.path.splitext(f)[1].lower() in ALLOWED_IMAGE_EXTS)
    return [CUSTOM_IMAGE_LABEL] + files

def list_sounds():
    """Return available sounds (.mp3, .wav) with the custom-import option first."""
    if not os.path.isdir(SOUNDS_DIR):
        return [CUSTOM_SOUND_LABEL]
    files = sorted(f for f in os.listdir(SOUNDS_DIR)
                   if os.path.splitext(f)[1].lower() in ALLOWED_SOUND_EXTS)
    return [CUSTOM_SOUND_LABEL] + files

def get_popup(cfg, trigger):
    for p in cfg.get("popups", []):
        if p.get("trigger") == trigger:
            return p
    return {"trigger": trigger, "message": "", "image": "", "sound": "", "sound_repeat": 1}

def get_break_milestones(cfg):
    """Return all break_end popups that have a non-zero duration (i.e. not the cycle-end entry)."""
    return [p for p in cfg.get("popups", [])
            if p.get("trigger") == "break_end"
            and (p.get("duration_min", 0) > 0 or p.get("duration_sec", 0) > 0)]

def get_cycle_end_popup(cfg):
    """
    Return the last break_end popup that has duration 0 — this is the
    'Cycle End' popup that fires last with no wait after it.
    Falls back to the last break_end popup overall, or a blank entry.
    """
    candidates = [p for p in cfg.get("popups", []) if p.get("trigger") == "break_end"]
    # Prefer an explicit zero-duration entry
    for p in reversed(candidates):
        if p.get("duration_min", 0) == 0 and p.get("duration_sec", 0) == 0:
            return p
    # Otherwise use the last break_end entry as cycle-end (remove from milestones)
    if candidates:
        return candidates[-1]
    return {"trigger": "break_end", "message": "", "image": "", "sound": "", "sound_repeat": 1,
            "duration_min": 0, "duration_sec": 0}

def fmt_duration(total_sec):
    """Format total seconds as  Xm Ys  string."""
    m, s = divmod(int(total_sec), 60)
    if m and s:
        return f"{m}m {s}s"
    elif m:
        return f"{m}m"
    else:
        return f"{s}s"

def _make_min_sec_widgets(parent, var_min, var_sec, bg, font,
                          min_max=999, sec_max=59):
    tk.Spinbox(parent, from_=0, to=min_max, width=4,
               textvariable=var_min, font=font,
               relief="solid", bd=1, highlightthickness=0, bg=bg
               ).pack(side="left")
    tk.Label(parent, text=" m", font=font, bg=bg, fg="#444444").pack(side="left")
    tk.Spinbox(parent, from_=0, to=sec_max, width=4,
               textvariable=var_sec, font=font,
               relief="solid", bd=1, highlightthickness=0, bg=bg
               ).pack(side="left")
    tk.Label(parent, text=" s", font=font, bg=bg, fg="#444444").pack(side="left")


def _import_custom_file(src_path, dest_dir, allowed_exts):
    """
    Copy src_path into dest_dir if the extension is allowed.
    Returns the filename on success, or None on failure.
    """
    ext = os.path.splitext(src_path)[1].lower()
    if ext not in allowed_exts:
        messagebox.showerror(
            "Unsupported Format",
            f"File type '{ext}' is not supported.\nAllowed: {', '.join(allowed_exts)}"
        )
        return None
    os.makedirs(dest_dir, exist_ok=True)
    filename = os.path.basename(src_path)
    dest_path = os.path.join(dest_dir, filename)
    if os.path.abspath(src_path) != os.path.abspath(dest_path):
        shutil.copy2(src_path, dest_path)
    return filename


def _build_image_row(parent, var_img, figures_list_ref, bg, font, fg, fg_light):
    """
    Build an image selection row: combobox + thumbnail preview.
    The first dropdown item opens a file dialog to import a custom image.
    figures_list_ref is a list that the caller may update; the combobox
    values are refreshed after a successful import.
    Returns (combobox, preview_label).
    """
    cb = ttk.Combobox(parent, textvariable=var_img,
                      values=figures_list_ref, width=22, font=font, state="normal")
    cb.pack(side="left")

    prev_lbl = tk.Label(parent, bg=bg)
    prev_lbl.pack(side="left", padx=(8, 0))

    def _refresh_preview(*_):
        val = var_img.get()
        if val == CUSTOM_IMAGE_LABEL or not val:
            prev_lbl.config(image="")
            return
        path = os.path.join(FIGURES_DIR, val)
        if os.path.exists(path):
            try:
                img = Image.open(path).resize((32, 32))
                ph  = ImageTk.PhotoImage(img)
                prev_lbl.config(image=ph); prev_lbl._photo = ph
            except Exception:
                prev_lbl.config(image="")
        else:
            prev_lbl.config(image="")

    def _on_select(event=None):
        val = var_img.get()
        if val != CUSTOM_IMAGE_LABEL:
            _refresh_preview()
            return
        # Open file dialog
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
            ]
        )
        if not path:
            var_img.set("")
            return
        fname = _import_custom_file(path, FIGURES_DIR, ALLOWED_IMAGE_EXTS)
        if fname:
            # Refresh dropdown values
            new_list = list_figures()
            figures_list_ref[:] = new_list
            cb["values"] = new_list
            var_img.set(fname)
            _refresh_preview()
        else:
            var_img.set("")

    cb.bind("<<ComboboxSelected>>", _on_select)
    var_img.trace_add("write", _refresh_preview)
    _refresh_preview()

    return cb, prev_lbl


def _build_sound_row(parent, var_snd, sounds_list_ref, bg, font, fg, fg_light):
    """
    Build a sound selection row: combobox + Play Sound button.
    The first dropdown item opens a file dialog to import a custom sound.
    Auto-plays the sound when the user actively selects from the dropdown.
    sounds_list_ref is a list that may be updated after a successful import.
    Returns the combobox widget.
    """
    cb = ttk.Combobox(parent, textvariable=var_snd,
                      values=sounds_list_ref, width=20, font=font, state="normal")
    cb.pack(side="left")

    def _play_current(*_):
        snd = var_snd.get().strip()
        if snd and snd != CUSTOM_SOUND_LABEL:
            preview_sound(os.path.join(SOUNDS_DIR, snd))

    def _on_select(event=None):
        val = var_snd.get()
        if val != CUSTOM_SOUND_LABEL:
            _play_current()
            return
        # Open file dialog
        path = filedialog.askopenfilename(
            title="Select Sound",
            filetypes=[
                ("Audio files", "*.mp3 *.wav"),
                ("MP3", "*.mp3"),
                ("WAV", "*.wav"),
            ]
        )
        if not path:
            var_snd.set("")
            return
        fname = _import_custom_file(path, SOUNDS_DIR, ALLOWED_SOUND_EXTS)
        if fname:
            new_list = list_sounds()
            sounds_list_ref[:] = new_list
            cb["values"] = new_list
            var_snd.set(fname)
            _play_current()
        else:
            var_snd.set("")

    cb.bind("<<ComboboxSelected>>", _on_select)

    play_btn = tk.Button(
        parent,
        text="▶  Play Sound",
        font=("Segoe UI", 9),
        bg="#e8f0fe", fg="#1a73e8",
        activebackground="#c5d5f5", activeforeground="#1a73e8",
        relief="flat", cursor="hand2",
        padx=8, pady=2, bd=0,
        command=_play_current,
    )
    play_btn.pack(side="left", padx=(6, 0))

    return cb


# ====================== BREAK MILESTONE MANAGER ======================

class BreakMilestoneManager:
    PANEL    = "#ffffff"
    ACCENT   = "#1a73e8"
    FG       = "#222222"
    FG_LIGHT = "#666666"
    BORDER   = "#e0e0e0"
    CARD_BG  = "#f0f4ff"
    FONT_MAIN  = ("Segoe UI", 10)
    FONT_TITLE = ("Segoe UI Semibold", 11)

    def __init__(self, parent, figures, sounds, on_entries_changed=None):
        self.parent          = parent
        self.figures         = figures
        self.sounds          = sounds
        self._on_changed     = on_entries_changed
        self._entries        = []
        self._cycle_end_vars = {}   # populated by _build_cycle_end_section

        self._build_header()
        self._empty_label = tk.Label(
            self.parent,
            text="No break milestones yet. Click '＋ Add Milestone' to create one.",
            font=("Segoe UI", 9), bg=self.PANEL, fg="#aaaaaa", justify="center",
        )
        # Cycle End section is built last (after milestones) but must exist before _repack
        self._build_cycle_end_section()

    def _build_header(self):
        self._header = tk.Frame(self.parent, bg=self.PANEL)
        self._header.pack(fill="x", padx=2, pady=(4, 4))
        tk.Frame(self._header, bg=self.ACCENT, width=4).pack(
            side="left", fill="y", padx=(0, 8))
        tk.Label(self._header, text="🔔  Break Milestone Popups",
                 font=("Segoe UI Semibold", 11),
                 bg=self.PANEL, fg=self.FG).pack(side="left")
        tk.Label(self._header, text="(triggered sequentially during break)",
                 font=("Segoe UI", 8),
                 bg=self.PANEL, fg=self.FG_LIGHT).pack(side="left", padx=(8, 0))
        tk.Button(self._header, text="＋  Add Milestone",
                  font=("Segoe UI Semibold", 9), bg=self.ACCENT, fg="white",
                  activebackground="#1558b0", activeforeground="white",
                  relief="flat", cursor="hand2", padx=10, pady=3, bd=0,
                  command=self._add_entry).pack(side="right", padx=(0, 2))

    def _build_cycle_end_section(self):
        """
        Build the fixed 'Cycle End' LabelFrame and store it as self._cycle_end_section.
        The widget is NOT packed here — _repack() packs it last every time so it
        always sits below every milestone card, even after add / delete / reorder.
        """
        section = tk.LabelFrame(
            self.parent,
            text="  \U0001f3c1  Cycle End  —  last popup before new cycle starts  ",
            font=self.FONT_TITLE,
            bg=self.PANEL, fg=self.ACCENT,
            relief="groove", bd=1, padx=10, pady=8,
        )
        # Do NOT call section.pack() here — _repack() controls placement
        self._cycle_end_section = section

        info = tk.Frame(section, bg=self.PANEL)
        info.pack(fill="x", pady=(0, 6))
        tk.Label(
            info,
            text=("This popup fires after the last Break Milestone.\n"
                  "It has no wait time — a new work cycle begins immediately after it."),
            font=("Segoe UI", 8), bg=self.PANEL, fg=self.FG_LIGHT,
            justify="left", wraplength=500,
        ).pack(anchor="w")
        tk.Frame(section, height=1, bg=self.BORDER).pack(fill="x", pady=(0, 6))

        self._cycle_end_vars = {
            "message":      tk.StringVar(),
            "image":        tk.StringVar(),
            "sound":        tk.StringVar(),
            "sound_repeat": tk.StringVar(value="1"),
        }
        v = self._cycle_end_vars

        r_msg = tk.Frame(section, bg=self.PANEL); r_msg.pack(fill="x", pady=2)
        tk.Label(r_msg, text="Message", font=self.FONT_MAIN,
                 bg=self.PANEL, fg=self.FG, width=18, anchor="w").pack(side="left")
        tk.Entry(r_msg, textvariable=v["message"], width=42, font=self.FONT_MAIN,
                 relief="solid", bd=1, highlightthickness=0
                 ).pack(side="left", fill="x", expand=True)

        r_img = tk.Frame(section, bg=self.PANEL); r_img.pack(fill="x", pady=2)
        tk.Label(r_img, text="Image", font=self.FONT_MAIN,
                 bg=self.PANEL, fg=self.FG, width=18, anchor="w").pack(side="left")
        figures_list = list_figures()
        _build_image_row(r_img, v["image"], figures_list,
                         bg=self.PANEL, font=self.FONT_MAIN,
                         fg=self.FG, fg_light=self.FG_LIGHT)

        r_snd = tk.Frame(section, bg=self.PANEL); r_snd.pack(fill="x", pady=2)
        tk.Label(r_snd, text="Sound", font=self.FONT_MAIN,
                 bg=self.PANEL, fg=self.FG, width=18, anchor="w").pack(side="left")
        sounds_list = list_sounds()
        _build_sound_row(r_snd, v["sound"], sounds_list,
                         bg=self.PANEL, font=self.FONT_MAIN,
                         fg=self.FG, fg_light=self.FG_LIGHT)
        tk.Label(r_snd, text="  Repeat", font=self.FONT_MAIN,
                 bg=self.PANEL, fg=self.FG).pack(side="left")
        tk.Spinbox(r_snd, from_=1, to=10, width=4, textvariable=v["sound_repeat"],
                   font=self.FONT_MAIN, relief="solid", bd=1,
                   highlightthickness=0).pack(side="left", padx=(4, 0))

    def _add_entry(self, data=None):
        if data is None:
            data = {"message": "", "image": "", "sound": "",
                    "sound_repeat": 1, "duration_min": 0, "duration_sec": 30}
        entry = {
            "message":      tk.StringVar(value=data.get("message", "")),
            "image":        tk.StringVar(value=data.get("image", "")),
            "sound":        tk.StringVar(value=data.get("sound", "")),
            "sound_repeat": tk.StringVar(value=str(data.get("sound_repeat", 1))),
            "duration_min": tk.StringVar(value=str(data.get("duration_min", 0))),
            "duration_sec": tk.StringVar(value=str(data.get("duration_sec", 30))),
            "frame":        None,
            "_idx_label":   None,
        }
        frame = self._build_entry_frame(entry)
        entry["frame"] = frame
        self._entries.append(entry)
        self._repack()
        if self._on_changed:
            self._on_changed()

    def _build_entry_frame(self, entry):
        frame = tk.Frame(self.parent, bg=self.PANEL)
        card  = tk.Frame(frame, bg=self.CARD_BG, relief="flat", bd=0,
                         highlightbackground="#c5d5f5", highlightthickness=1)
        card.pack(fill="x", padx=6, pady=3, ipady=5, ipadx=8)

        # Top row
        top = tk.Frame(card, bg=self.CARD_BG)
        top.pack(fill="x", pady=(0, 4))
        idx_lbl = tk.Label(top, text="", font=("Segoe UI Semibold", 9),
                           bg=self.CARD_BG, fg=self.ACCENT)
        idx_lbl.pack(side="left")
        entry["_idx_label"] = idx_lbl

        bc = dict(font=("Segoe UI", 9), relief="flat", cursor="hand2", padx=6, pady=2, bd=0)
        bf = tk.Frame(top, bg=self.CARD_BG); bf.pack(side="right")
        tk.Button(bf, text="▲", bg="#e8e8e8", fg=self.FG, **bc,
                  command=lambda: self._move_entry(entry, -1)).pack(side="left", padx=2)
        tk.Button(bf, text="▼", bg="#e8e8e8", fg=self.FG, **bc,
                  command=lambda: self._move_entry(entry, +1)).pack(side="left", padx=2)
        tk.Button(bf, text="✕  Delete", bg="#ffeded", fg="#cc0000",
                  activebackground="#ffcccc", activeforeground="#990000", **bc,
                  command=lambda: self._delete_entry(entry)).pack(side="left", padx=(6, 0))

        # ── Popup content (fires first) ───────────────────────────────
        # Message
        r_msg = tk.Frame(card, bg=self.CARD_BG); r_msg.pack(fill="x", pady=2)
        tk.Label(r_msg, text="Message", font=self.FONT_MAIN,
                 bg=self.CARD_BG, fg=self.FG, width=18, anchor="w").pack(side="left")
        tk.Entry(r_msg, textvariable=entry["message"], width=38, font=self.FONT_MAIN,
                 relief="solid", bd=1, highlightthickness=0
                 ).pack(side="left", fill="x", expand=True)

        # Image
        r_img = tk.Frame(card, bg=self.CARD_BG); r_img.pack(fill="x", pady=2)
        tk.Label(r_img, text="Image", font=self.FONT_MAIN,
                 bg=self.CARD_BG, fg=self.FG, width=18, anchor="w").pack(side="left")
        figures_list = list_figures()
        _build_image_row(r_img, entry["image"], figures_list,
                         bg=self.CARD_BG, font=self.FONT_MAIN,
                         fg=self.FG, fg_light=self.FG_LIGHT)

        # Sound + Repeat
        r_snd = tk.Frame(card, bg=self.CARD_BG); r_snd.pack(fill="x", pady=2)
        tk.Label(r_snd, text="Sound", font=self.FONT_MAIN,
                 bg=self.CARD_BG, fg=self.FG, width=18, anchor="w").pack(side="left")
        sounds_list = list_sounds()
        _build_sound_row(r_snd, entry["sound"], sounds_list,
                         bg=self.CARD_BG, font=self.FONT_MAIN,
                         fg=self.FG, fg_light=self.FG_LIGHT)
        tk.Label(r_snd, text="  Repeat", font=self.FONT_MAIN,
                 bg=self.CARD_BG, fg=self.FG).pack(side="left")
        tk.Spinbox(r_snd, from_=1, to=10, width=4, textvariable=entry["sound_repeat"],
                   font=self.FONT_MAIN, relief="solid", bd=1,
                   highlightthickness=0).pack(side="left", padx=(4, 0))

        # ── Divider before duration ───────────────────────────────────
        tk.Frame(card, height=1, bg="#c5d5f5").pack(fill="x", pady=(8, 4))

        # ── Duration (wait after this popup fires) ────────────────────
        r_dur = tk.Frame(card, bg=self.CARD_BG); r_dur.pack(fill="x", pady=(2, 0))
        tk.Label(r_dur,
                 text="⏳  Then wait",
                 font=("Segoe UI Semibold", 9),
                 bg=self.CARD_BG, fg=self.ACCENT,
                 width=18, anchor="w").pack(side="left")
        _make_min_sec_widgets(r_dur, entry["duration_min"], entry["duration_sec"],
                              bg=self.CARD_BG, font=self.FONT_MAIN)
        tk.Label(r_dur,
                 text="  before next popup",
                 font=("Segoe UI", 8), bg=self.CARD_BG,
                 fg=self.FG_LIGHT).pack(side="left", padx=(6, 0))

        return frame

    def _delete_entry(self, entry):
        self._entries.remove(entry)
        entry["frame"].destroy()
        self._repack()
        if self._on_changed:
            self._on_changed()

    def _move_entry(self, entry, direction):
        idx = self._entries.index(entry)
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self._entries):
            return
        self._entries[idx], self._entries[new_idx] = \
            self._entries[new_idx], self._entries[idx]
        self._repack()
        if self._on_changed:
            self._on_changed()

    def _repack(self):
        """
        Re-pack all dynamic widgets in the correct order:
          [empty label OR milestone cards]  →  [Cycle End section always last]
        """
        # 1. Hide everything that we control
        self._empty_label.pack_forget()
        for e in self._entries:
            e["frame"].pack_forget()
        self._cycle_end_section.pack_forget()

        # 2. Pack milestones (or the placeholder label)
        if not self._entries:
            self._empty_label.pack(fill="x", padx=8, pady=6)
        else:
            for i, e in enumerate(self._entries):
                e["frame"].pack(fill="x")
                e["_idx_label"].config(text=f"Milestone #{i + 1}")

        # 3. Always pack Cycle End section last so it stays at the bottom
        self._cycle_end_section.pack(fill="x", padx=2, pady=(10, 4))

    def load_milestones(self, milestone_list):
        for e in list(self._entries):
            e["frame"].destroy()
        self._entries.clear()
        self._empty_label.pack_forget()
        for data in milestone_list:
            self._add_entry(data)

    def collect_milestones(self):
        result = []
        for e in self._entries:
            try: repeat = int(e["sound_repeat"].get())
            except ValueError: repeat = 1
            try: dur_min = int(e["duration_min"].get())
            except ValueError: dur_min = 0
            try: dur_sec = int(e["duration_sec"].get())
            except ValueError: dur_sec = 30
            result.append({
                "trigger":      "break_end",
                "message":      e["message"].get().strip(),
                "image":        e["image"].get().strip(),
                "sound":        e["sound"].get().strip(),
                "sound_repeat": max(1, repeat),
                "duration_min": max(0, dur_min),
                "duration_sec": max(0, min(59, dur_sec)),
            })
        return result

    def load_cycle_end(self, data):
        v = self._cycle_end_vars
        v["message"].set(data.get("message", ""))
        v["image"].set(data.get("image", ""))
        v["sound"].set(data.get("sound", ""))
        v["sound_repeat"].set(str(data.get("sound_repeat", 1)))

    def collect_cycle_end(self):
        v = self._cycle_end_vars
        try: repeat = int(v["sound_repeat"].get())
        except ValueError: repeat = 1
        return {
            "trigger":      "break_end",
            "message":      v["message"].get().strip(),
            "image":        v["image"].get().strip(),
            "sound":        v["sound"].get().strip(),
            "sound_repeat": max(1, repeat),
            "duration_min": 0,
            "duration_sec": 0,
        }

    @property
    def entries(self):
        return self._entries


# ====================== PROFESSIONAL TOGGLE SWITCH ======================

class ToggleSwitch(tk.Canvas):
    """
    Professional iOS / Material-style animated toggle switch.

    Visual design:
    • Larger pill track (56 × 28 px) with subtle inner shadow
    • Elevated white thumb with drop-shadow ring
    • Smooth colour transition between ON (#1a73e8) and OFF (#b0b8c1)
    • 12-frame eased animation at ~60 fps
    • Cursor changes to hand on hover
    """

    W, H   = 56, 28          # track dimensions
    PAD    = 3                # thumb inset from track edge
    STEPS  = 12               # animation frames

    # Colour palette
    ON_TRACK  = "#1a73e8"     # Google Blue
    OFF_TRACK = "#b0b8c1"     # cool grey
    THUMB_CLR = "#ffffff"
    SHADOW_CLR= "#d0d8e4"     # thumb drop-shadow ring colour

    def __init__(self, parent, variable, **kwargs):
        super().__init__(parent,
                         width=self.W, height=self.H,
                         highlightthickness=0, bd=0, **kwargs)
        self._var       = variable
        self._animating = False
        self._cur_ratio = 0.0   # 0.0 = fully OFF, 1.0 = fully ON

        self._draw()
        self.bind("<Button-1>",  self._on_click)
        self.bind("<Enter>",     lambda _: self.config(cursor="hand2"))
        self.bind("<Leave>",     lambda _: self.config(cursor=""))
        self._var.trace_add("write", self._on_var_change)
        self._apply_state(animate=False)

    # ── Drawing ────────────────────────────────────────────────────────

    def _lerp_color(self, c1, c2, t):
        """Linear interpolate between two #rrggbb hex colours."""
        r1, g1, b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
        r2, g2, b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
        r = int(r1 + (r2-r1)*t)
        g = int(g1 + (g2-g1)*t)
        b = int(b1 + (b2-b1)*t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _thumb_x(self):
        """Compute thumb left-x from current ratio."""
        travel = self.W - self.H           # how far the thumb travels
        return self.PAD + self._cur_ratio * travel

    def _draw(self):
        """Redraw the entire widget from scratch based on _cur_ratio."""
        self.delete("all")

        # ── Track ──────────────────────────────────────────────────────
        track_color = self._lerp_color(self.OFF_TRACK, self.ON_TRACK, self._cur_ratio)
        r = self.H / 2
        self._draw_pill(0, 0, self.W, self.H, r, track_color)

        # ── Thumb shadow ring ──────────────────────────────────────────
        tx = self._thumb_x()
        td = self.H - 2 * self.PAD         # thumb diameter
        shadow_pad = 1
        self.create_oval(
            tx - shadow_pad, self.PAD - shadow_pad,
            tx + td + shadow_pad, self.PAD + td + shadow_pad,
            fill=self.SHADOW_CLR, outline=""
        )

        # ── Thumb ──────────────────────────────────────────────────────
        self.create_oval(tx, self.PAD, tx + td, self.PAD + td,
                         fill=self.THUMB_CLR, outline="")

        # ── ON / OFF label inside track ────────────────────────────────
        label_alpha = self._cur_ratio
        if label_alpha > 0.55:
            self.create_text(
                self.W * 0.28, self.H / 2,
                text="ON", fill="white",
                font=("Segoe UI Semibold", 7)
            )
        else:
            self.create_text(
                self.W * 0.72, self.H / 2,
                text="OFF", fill="white",
                font=("Segoe UI Semibold", 7)
            )

    def _draw_pill(self, x1, y1, x2, y2, r, color):
        pts = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
               x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
               x1, y2, x1, y2-r, x1, y1+r, x1, y1]
        self.create_polygon(pts, smooth=True, fill=color, outline="")

    # ── Interaction ────────────────────────────────────────────────────

    def _on_click(self, _=None):
        self._var.set(not self._var.get())

    def _on_var_change(self, *_):
        self._apply_state(animate=True)

    def _apply_state(self, animate=True):
        target = 1.0 if self._var.get() else 0.0
        if animate and not self._animating:
            self._animate_to(target, self.STEPS)
        else:
            self._cur_ratio = target
            self._draw()

    def _ease(self, t):
        """Ease-in-out cubic."""
        return t * t * (3 - 2 * t)

    def _animate_to(self, target, steps_left):
        if steps_left <= 0:
            self._cur_ratio = target
            self._draw()
            self._animating = False
            return
        self._animating = True
        # Move a fraction of the remaining distance (eased)
        remaining = target - self._cur_ratio
        self._cur_ratio += remaining / steps_left
        self._draw()
        self.after(16, lambda: self._animate_to(target, steps_left - 1))


# ====================== GUI ======================

class ConfigApp(tk.Tk):
    FONT_MAIN  = ("Segoe UI", 10)
    FONT_TITLE = ("Segoe UI Semibold", 11)
    FONT_HEAD  = ("Segoe UI Semibold", 13)
    BG         = "#f5f5f5"
    ACCENT     = "#1a73e8"
    PANEL      = "#ffffff"
    BORDER     = "#e0e0e0"
    FG         = "#222222"
    FG_LIGHT   = "#666666"
    READONLY   = "#eeeeee"

    def __init__(self):
        super().__init__()
        self.title("EyeGuard Configurator")
        self.resizable(False, True)
        self.configure(bg=self.BG)

        if os.path.exists(ICON_PATH):
            try:
                icon = ImageTk.PhotoImage(Image.open(ICON_PATH).resize((32, 32)))
                self.iconphoto(True, icon)
                self._icon_ref = icon
            except Exception:
                pass

        self.cfg              = load_config()
        # Show any config-load error now that Tk exists
        if load_config.error:
            messagebox.showerror(
                "Load Error",
                f"Could not read config.json:\n{load_config.error}\n\nUsing defaults.")
        self._timer_rows      = []
        self.var_test         = tk.BooleanVar()
        self.var_cycle_align  = tk.BooleanVar()

        self._build_ui()
        self._populate()

        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w    = max(self.winfo_reqwidth(), 1240)
        win_h    = int(screen_h * 0.88)
        x        = (screen_w - win_w) // 2
        y        = (screen_h - win_h) // 2
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")

    # ------------------------------------------------------------------
    # UI BUILD HELPERS
    # ------------------------------------------------------------------

    def _card(self, parent, title=None):
        outer = tk.Frame(parent, bg=self.BORDER, bd=0)
        inner = tk.Frame(outer, bg=self.PANEL, padx=16, pady=14)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        if title:
            tk.Label(inner, text=title, font=self.FONT_HEAD,
                     bg=self.PANEL, fg=self.FG).pack(anchor="w", pady=(0, 10))
        return outer, inner

    def _entry(self, parent, width=38, **kw):
        return tk.Entry(parent, width=width, font=self.FONT_MAIN,
                        relief="solid", bd=1, highlightthickness=0, **kw)

    def _row(self, parent, label, widget_factory, **kw):
        row = tk.Frame(parent, bg=self.PANEL)
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, font=self.FONT_MAIN,
                 bg=self.PANEL, fg=self.FG, width=18, anchor="w").pack(side="left")
        w = widget_factory(row, **kw)
        w.pack(side="left", fill="x", expand=True)
        return w

    def _spinbox(self, parent, from_=1, to=600, width=6, **kw):
        return tk.Spinbox(parent, from_=from_, to=to, width=width,
                          font=self.FONT_MAIN, relief="solid", bd=1,
                          highlightthickness=0, **kw)

    # ------------------------------------------------------------------
    # FIXED POPUP SECTION
    # ------------------------------------------------------------------

    def _build_fixed_popup_section(self, parent, trigger, figures, sounds,
                                   pack=True,
                                   extra_timer_var_min=None,
                                   extra_timer_var_sec=None,
                                   extra_timer_label=None,
                                   time_only=False):
        """
        Build a fixed popup section.

        time_only=True  →  Only a duration row is shown (no message/image/sound).
                           Used for the Work Time block, which just defines how
                           long the work phase lasts after the popup fires.
        """
        section = tk.LabelFrame(
            parent,
            text=f"  {TRIGGER_LABELS.get(trigger, trigger)}  ",
            font=self.FONT_TITLE,
            bg=self.PANEL, fg=self.ACCENT,
            relief="groove", bd=1, padx=10, pady=8,
        )
        if pack:
            section.pack(fill="x", pady=(0, 8), padx=2)

        if time_only:
            # ── Work Time block: duration only, clear explanatory label ──
            info = tk.Frame(section, bg=self.PANEL)
            info.pack(fill="x", pady=(0, 6))
            tk.Label(
                info,
                text=("The Work End popup fires immediately at the start of each cycle.\n"
                      "Set how long the work phase lasts before the first Break Milestone popup appears."),
                font=("Segoe UI", 8), bg=self.PANEL, fg=self.FG_LIGHT,
                justify="left", wraplength=480,
            ).pack(anchor="w")

            tk.Frame(section, height=1, bg=self.BORDER).pack(fill="x", pady=(0, 8))

            t_row = tk.Frame(section, bg=self.PANEL)
            t_row.pack(fill="x", pady=3)
            tk.Label(t_row, text="Work Duration", font=self.FONT_MAIN,
                     bg=self.PANEL, fg=self.FG,
                     width=14, anchor="w").pack(side="left")
            _make_min_sec_widgets(t_row, extra_timer_var_min, extra_timer_var_sec,
                                  bg=self.PANEL, font=self.FONT_MAIN,
                                  min_max=999, sec_max=59)
            tk.Label(t_row,
                     text="  ← also shown in Timer Settings",
                     font=("Segoe UI", 8), bg=self.PANEL,
                     fg=self.FG_LIGHT).pack(side="left", padx=(8, 0))

            return section, None   # no popup vars for time-only block

        # ── Normal popup section (message / image / sound) ────────────
        if extra_timer_var_min is not None:
            t_row = tk.Frame(section, bg=self.PANEL); t_row.pack(fill="x", pady=3)
            tk.Label(t_row, text=extra_timer_label, font=self.FONT_MAIN,
                     bg=self.PANEL, fg=self.ACCENT,
                     width=14, anchor="w").pack(side="left")
            _make_min_sec_widgets(t_row, extra_timer_var_min, extra_timer_var_sec,
                                  bg=self.PANEL, font=self.FONT_MAIN,
                                  min_max=999, sec_max=59)
            tk.Label(t_row, text="  ← shared with Timer Settings",
                     font=("Segoe UI", 8), bg=self.PANEL,
                     fg=self.FG_LIGHT).pack(side="left", padx=(6, 0))
            tk.Frame(section, height=1, bg=self.BORDER).pack(fill="x", pady=(4, 6))

        mr = tk.Frame(section, bg=self.PANEL); mr.pack(fill="x", pady=3)
        tk.Label(mr, text="Message", font=self.FONT_MAIN,
                 bg=self.PANEL, fg=self.FG, width=14, anchor="w").pack(side="left")
        var_msg = tk.StringVar()
        tk.Entry(mr, textvariable=var_msg, width=42, font=self.FONT_MAIN,
                 relief="solid", bd=1, highlightthickness=0
                 ).pack(side="left", fill="x", expand=True)

        ir = tk.Frame(section, bg=self.PANEL); ir.pack(fill="x", pady=3)
        tk.Label(ir, text="Image", font=self.FONT_MAIN,
                 bg=self.PANEL, fg=self.FG, width=14, anchor="w").pack(side="left")
        var_img = tk.StringVar()
        figures_list = list_figures()
        _build_image_row(ir, var_img, figures_list,
                         bg=self.PANEL, font=self.FONT_MAIN,
                         fg=self.FG, fg_light=self.FG_LIGHT)

        sr = tk.Frame(section, bg=self.PANEL); sr.pack(fill="x", pady=3)
        tk.Label(sr, text="Sound", font=self.FONT_MAIN,
                 bg=self.PANEL, fg=self.FG, width=14, anchor="w").pack(side="left")
        var_snd = tk.StringVar()
        sounds_list = list_sounds()
        _build_sound_row(sr, var_snd, sounds_list,
                         bg=self.PANEL, font=self.FONT_MAIN,
                         fg=self.FG, fg_light=self.FG_LIGHT)
        tk.Label(sr, text="  Repeat", font=self.FONT_MAIN,
                 bg=self.PANEL, fg=self.FG).pack(side="left")
        var_rep = tk.StringVar()
        tk.Spinbox(sr, from_=1, to=10, width=4, textvariable=var_rep,
                   font=self.FONT_MAIN, relief="solid", bd=1,
                   highlightthickness=0).pack(side="left", padx=(4, 0))

        return section, {"message": var_msg, "image": var_img,
                         "sound": var_snd, "sound_repeat": var_rep}

    # ------------------------------------------------------------------
    # TIMER PANEL — totals + dynamic milestone rows
    # ------------------------------------------------------------------

    def _update_totals(self, *_):
        try:
            work_s = int(self.var_work_min.get()) * 60 + int(self.var_work_sec.get())
        except ValueError:
            work_s = 0

        break_s = 0
        for e in self._milestone_manager.entries:
            try:
                break_s += int(e["duration_min"].get()) * 60 + int(e["duration_sec"].get())
            except ValueError:
                pass

        self._var_total_break.set(fmt_duration(break_s) if break_s else "0s")
        self._var_total_cycle.set(fmt_duration(work_s + break_s) if (work_s + break_s) else "0s")

    def _maybe_enable_timer_scroll(self):
        self._timer_canvas.update_idletasks()
        content_h = self._timer_canvas_frame.winfo_reqheight()
        canvas_h  = self._timer_canvas.winfo_height()
        if content_h > canvas_h:
            if not self._timer_vsb.winfo_ismapped():
                self._timer_vsb.pack(side="right", fill="y",
                                     before=self._timer_canvas)
            self._timer_canvas.bind_all(
                "<MouseWheel>",
                lambda ev: self._timer_canvas.yview_scroll(
                    int(-1 * (ev.delta / 120)), "units"))
        else:
            if self._timer_vsb.winfo_ismapped():
                self._timer_vsb.pack_forget()
            self._timer_canvas.unbind_all("<MouseWheel>")

    def _rebuild_timer_milestone_rows(self):
        entries = self._milestone_manager.entries

        self._total_break_row.pack_forget()
        self._total_cycle_row.pack_forget()

        for frame, _ in self._timer_rows:
            frame.destroy()
        self._timer_rows.clear()

        for i, entry in enumerate(entries):
            row = tk.Frame(self._timer_canvas_frame, bg=self.PANEL)
            row.pack(fill="x", pady=4)
            lbl = tk.Label(row, text=f"Milestone {i + 1} Duration",
                           font=self.FONT_MAIN, bg=self.PANEL, fg=self.FG,
                           width=18, anchor="w")
            lbl.pack(side="left")
            _make_min_sec_widgets(row,
                                  entry["duration_min"], entry["duration_sec"],
                                  bg=self.PANEL, font=self.FONT_MAIN,
                                  min_max=999, sec_max=59)
            entry["duration_min"].trace_add("write", self._update_totals)
            entry["duration_sec"].trace_add("write", self._update_totals)
            self._timer_rows.append((row, lbl))

        self._total_break_row.pack(fill="x", pady=4)
        self._total_cycle_row.pack(fill="x", pady=4)

        self._update_totals()
        self._timer_canvas_frame.update_idletasks()
        self._timer_canvas.configure(
            scrollregion=self._timer_canvas.bbox("all"))
        self._maybe_enable_timer_scroll()

    # ------------------------------------------------------------------
    # MAIN UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        figures = list_figures()
        sounds  = list_sounds()

        # ── Title bar ──────────────────────────────────────────────────
        title_bar = tk.Frame(self, bg=self.ACCENT)
        title_bar.pack(fill="x")
        tk.Label(title_bar, text="  EyeGuard Configurator",
                 font=("Segoe UI Semibold", 14), fg="white",
                 bg=self.ACCENT, pady=12).pack(side="left")

        # ── Main columns ───────────────────────────────────────────────
        body = tk.Frame(self, bg=self.BG)
        body.pack(fill="both", expand=True, padx=18, pady=12)

        left  = tk.Frame(body, bg=self.BG)
        right = tk.Frame(body, bg=self.BG)
        left.pack(side="left", fill="both", expand=False, padx=(0, 8))
        right.pack(side="left", fill="both", expand=True)

        # ══════════════════════════════════════════════════════════════
        # LEFT COLUMN
        # ══════════════════════════════════════════════════════════════

        # ── Timer Settings card ────────────────────────────────────────
        timer_card_outer = tk.Frame(left, bg=self.BORDER, bd=0)
        timer_card_outer.pack(fill="both", expand=True, pady=(0, 10))
        timer_card_inner = tk.Frame(timer_card_outer, bg=self.PANEL, padx=16, pady=14)
        timer_card_inner.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Label(timer_card_inner, text="⏱  Timer Settings",
                 font=self.FONT_HEAD, bg=self.PANEL,
                 fg=self.FG).pack(anchor="w", pady=(0, 6))

        timer_scroll_frame = tk.Frame(timer_card_inner, bg=self.PANEL)
        timer_scroll_frame.pack(fill="both", expand=True)

        self._timer_vsb    = ttk.Scrollbar(timer_scroll_frame, orient="vertical")
        self._timer_canvas = tk.Canvas(timer_scroll_frame, bg=self.PANEL,
                                       highlightthickness=0,
                                       yscrollcommand=self._timer_vsb.set)
        self._timer_vsb.configure(command=self._timer_canvas.yview)
        self._timer_canvas.pack(side="left", fill="both", expand=True)

        self._timer_canvas_frame = tk.Frame(self._timer_canvas, bg=self.PANEL)
        tc_win = self._timer_canvas.create_window(
            (0, 0), window=self._timer_canvas_frame, anchor="nw")

        def _on_timer_frame_configure(e):
            self._timer_canvas.configure(
                scrollregion=self._timer_canvas.bbox("all"))
            self._maybe_enable_timer_scroll()

        self._timer_canvas_frame.bind("<Configure>", _on_timer_frame_configure)
        self._timer_canvas.bind(
            "<Configure>",
            lambda e: (self._timer_canvas.itemconfig(tc_win, width=e.width),
                       self._maybe_enable_timer_scroll()))

        self._timer_pane = self._timer_canvas_frame

        # Work Time
        self.var_work_min = tk.StringVar()
        self.var_work_sec = tk.StringVar()
        wt_row = tk.Frame(self._timer_canvas_frame, bg=self.PANEL)
        wt_row.pack(fill="x", pady=4)
        tk.Label(wt_row, text="Work Time", font=self.FONT_MAIN,
                 bg=self.PANEL, fg=self.FG, width=18, anchor="w").pack(side="left")
        _make_min_sec_widgets(wt_row, self.var_work_min, self.var_work_sec,
                              bg=self.PANEL, font=self.FONT_MAIN,
                              min_max=999, sec_max=59)
        self.var_work_min.trace_add("write", self._update_totals)
        self.var_work_sec.trace_add("write", self._update_totals)

        # Total Break Time (read-only)
        self._var_total_break = tk.StringVar(value="—")
        self._total_break_row = tk.Frame(self._timer_canvas_frame, bg=self.PANEL)
        tk.Label(self._total_break_row, text="Total Break Time",
                 font=self.FONT_MAIN, bg=self.PANEL, fg=self.FG_LIGHT,
                 width=18, anchor="w").pack(side="left")
        tk.Entry(self._total_break_row, textvariable=self._var_total_break,
                 width=10, font=self.FONT_MAIN, relief="flat",
                 bg=self.READONLY, fg=self.FG_LIGHT,
                 state="readonly", readonlybackground=self.READONLY,
                 highlightthickness=0).pack(side="left")

        # Total Cycle Time (read-only) — label + entry aligned identically to rows above
        self._var_total_cycle = tk.StringVar(value="—")
        self._total_cycle_row = tk.Frame(self._timer_canvas_frame, bg=self.PANEL)
        tk.Label(self._total_cycle_row, text="Total Cycle Time",
                 font=self.FONT_MAIN, bg=self.PANEL, fg=self.ACCENT,
                 width=18, anchor="w").pack(side="left")
        tk.Entry(self._total_cycle_row, textvariable=self._var_total_cycle,
                 width=10, font=self.FONT_MAIN, relief="flat",
                 bg=self.READONLY, fg=self.ACCENT,
                 state="readonly", readonlybackground=self.READONLY,
                 highlightthickness=0).pack(side="left")

        # ── Appearance ────────────────────────────────────────────────
        card2, pane2 = self._card(left, title="🎨  Appearance")
        card2.pack(fill="x", pady=(0, 10))

        self.var_font    = tk.StringVar()
        self.var_color   = tk.StringVar()
        self.var_opacity = tk.IntVar(value=100)

        op_row = tk.Frame(pane2, bg=self.PANEL)
        op_row.pack(fill="x", pady=4)
        tk.Label(op_row, text="Popup Opacity", font=self.FONT_MAIN,
                 bg=self.PANEL, fg=self.FG,
                 width=18, anchor="w").pack(side="left")
        tk.Spinbox(op_row, from_=10, to=100, width=5,
                   textvariable=self.var_opacity,
                   font=self.FONT_MAIN, relief="solid", bd=1,
                   highlightthickness=0).pack(side="left")
        tk.Label(op_row, text=" %", font=self.FONT_MAIN,
                 bg=self.PANEL, fg="#444444").pack(side="left")
        ttk.Scale(op_row, from_=10, to=100,
                  orient="horizontal",
                  variable=self.var_opacity,
                  command=lambda v: self.var_opacity.set(int(float(v)))
                  ).pack(side="left", padx=(10, 0), fill="x", expand=True)

        tk.Frame(pane2, height=1, bg=self.BORDER).pack(fill="x", pady=(4, 8))

        self._row(pane2, "Font Name",  self._entry,
                  textvariable=self.var_font,  width=26)
        self._row(pane2, "Text Color", self._entry,
                  textvariable=self.var_color, width=26)
        tk.Label(pane2, text="Use hex color codes, e.g. #222222",
                 font=("Segoe UI", 8), bg=self.PANEL,
                 fg=self.FG_LIGHT).pack(anchor="w", padx=(140, 0))

        # ── Advanced Features ─────────────────────────────────────────
        card3, pane3 = self._card(left, title="⚙️  Advanced Features")
        card3.pack(fill="x")

        tm_row = tk.Frame(pane3, bg=self.PANEL)
        tm_row.pack(fill="x", pady=(0, 8))
        tk.Label(tm_row, text="Test Mode (5 s)",
                 font=self.FONT_MAIN, bg=self.PANEL, fg=self.FG,
                 width=18, anchor="w").pack(side="left")
        ToggleSwitch(tm_row, variable=self.var_test,
                     bg=self.PANEL).pack(side="left")
        tk.Label(tm_row, text="  All intervals → 5 s",
                 font=("Segoe UI", 8), bg=self.PANEL,
                 fg=self.FG_LIGHT).pack(side="left")

        ca_row = tk.Frame(pane3, bg=self.PANEL)
        ca_row.pack(fill="x", pady=(0, 8))
        tk.Label(ca_row, text="30-Min Alignment",
                 font=self.FONT_MAIN, bg=self.PANEL, fg=self.FG,
                 width=18, anchor="w").pack(side="left")
        ToggleSwitch(ca_row, variable=self.var_cycle_align,
                     bg=self.PANEL).pack(side="left")
        tk.Label(ca_row, text="  Last milestone snaps to :00/:30 clock marks",
                 font=("Segoe UI", 8), bg=self.PANEL,
                 fg=self.FG_LIGHT).pack(side="left")

        tk.Frame(pane3, height=1, bg=self.BORDER).pack(fill="x", pady=(0, 10))

        # Professional reset button using ttk with a custom style
        style = ttk.Style()
        style.configure("Reset.TButton",
                         font=("Segoe UI", 10),
                         foreground="#444444",
                         background="#f0f0f0",
                         borderwidth=1,
                         relief="flat",
                         padding=(14, 7))
        style.map("Reset.TButton",
                  background=[("active", "#e0e0e0"), ("pressed", "#d0d0d0")],
                  foreground=[("active", "#222222")])

        ttk.Button(pane3, text="↺   Reset to Defaults",
                   style="Reset.TButton",
                   command=self._reset).pack(anchor="w")

        # ══════════════════════════════════════════════════════════════
        # RIGHT COLUMN — scrollable popup events
        # ══════════════════════════════════════════════════════════════
        right_card, right_pane = self._card(right)
        right_card.pack(fill="both", expand=True)

        tk.Label(right_pane, text="💬  Popup Events",
                 font=self.FONT_HEAD, bg=self.PANEL,
                 fg=self.FG).pack(anchor="w", pady=(0, 6))

        canvas = tk.Canvas(right_pane, bg=self.PANEL, highlightthickness=0)
        vsb    = ttk.Scrollbar(right_pane, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        scroll_frame = tk.Frame(canvas, bg=self.PANEL)
        cw = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        scroll_frame.bind("<Configure>",
                          lambda e: canvas.configure(
                              scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(cw, width=e.width))
        canvas.bind("<Enter>",
                    lambda e: canvas.bind_all(
                        "<MouseWheel>",
                        lambda ev: canvas.yview_scroll(
                            int(-1 * (ev.delta / 120)), "units")))
        canvas.bind("<Leave>",
                    lambda e: canvas.unbind_all("<MouseWheel>"))

        self._popup_frames = {}

        _, vars_start = self._build_fixed_popup_section(
            scroll_frame, "start", figures, sounds, pack=True)
        self._popup_frames["start"] = vars_start

        # Work End section: time-only — no popup fields, just the duration
        self._build_fixed_popup_section(
            scroll_frame, "work_end", figures, sounds, pack=True,
            extra_timer_var_min=self.var_work_min,
            extra_timer_var_sec=self.var_work_sec,
            extra_timer_label="Work Time",
            time_only=True,
        )
        # work_end popup content is saved/loaded directly via var_work_min / var_work_sec
        # and the fixed DEFAULT_CONFIG work_end popup entry — no runtime widget dict needed

        self._milestone_manager = BreakMilestoneManager(
            scroll_frame, figures=figures, sounds=sounds,
            on_entries_changed=self._rebuild_timer_milestone_rows,
        )

        # ── Buttons ───────────────────────────────────────────────────
        btn_bar = tk.Frame(self, bg=self.BG)
        btn_bar.pack(fill="x", padx=18, pady=(0, 14))

        bs = dict(font=("Segoe UI Semibold", 10), relief="flat",
                  cursor="hand2", padx=20, pady=8, bd=0)

        tk.Button(btn_bar, text="✔  Save Configuration",
                  bg=self.ACCENT, fg="white",
                  activebackground="#1558b0", activeforeground="white",
                  command=self._save, **bs).pack(side="right")

        tk.Label(self,
                 text="Developed by Ivan Sicaja © 2026. All rights reserved.",
                 font=("Segoe UI", 8), bg=self.BG, fg="#aaaaaa").pack(pady=(0, 6))

    # ------------------------------------------------------------------
    # POPULATE / SAVE / RESET
    # ------------------------------------------------------------------

    def _populate(self):
        self.var_work_min.set(str(self.cfg.get("work_time_min", 25)))
        self.var_work_sec.set(str(self.cfg.get("work_time_sec", 0)))
        self.var_opacity.set(int(self.cfg.get("popup_opacity", 100)))
        self.var_test.set(self.cfg.get("test_mode", False))
        self.var_cycle_align.set(self.cfg.get("cycle_align", False))
        self.var_font.set(self.cfg.get("font_name", "Montserrat"))
        self.var_color.set(self.cfg.get("message_color", "#222222"))

        for trigger, widgets in self._popup_frames.items():
            if widgets is None:
                continue   # time-only block — no widget fields to populate
            popup = get_popup(self.cfg, trigger)
            widgets["message"].set(popup.get("message", ""))
            widgets["image"].set(popup.get("image", ""))
            widgets["sound"].set(popup.get("sound", ""))
            widgets["sound_repeat"].set(str(popup.get("sound_repeat", 1)))

        milestones = get_break_milestones(self.cfg)
        if not milestones:
            milestones = [p for p in DEFAULT_CONFIG["popups"]
                          if p["trigger"] == "break_end"
                          and (p.get("duration_min", 0) > 0 or p.get("duration_sec", 0) > 0)]
        self._milestone_manager.load_milestones(milestones)

        cycle_end = get_cycle_end_popup(self.cfg)
        self._milestone_manager.load_cycle_end(cycle_end)

    def _collect(self):
        try:
            work_min = int(self.var_work_min.get())
            work_sec = int(self.var_work_sec.get())
        except ValueError:
            messagebox.showerror("Validation Error",
                                 "Work Time must be whole numbers.")
            return None

        popups = []
        for trigger in FIXED_TRIGGERS:
            w = self._popup_frames.get(trigger)
            if w is None:
                # time-only block (work_end): preserve existing popup data from cfg
                existing = get_popup(self.cfg, trigger)
                popups.append({
                    "trigger":      trigger,
                    "message":      existing.get("message", ""),
                    "image":        existing.get("image", ""),
                    "sound":        existing.get("sound", ""),
                    "sound_repeat": existing.get("sound_repeat", 1),
                })
            else:
                try: repeat = int(w["sound_repeat"].get())
                except ValueError: repeat = 1
                popups.append({
                    "trigger":      trigger,
                    "message":      w["message"].get().strip(),
                    "image":        w["image"].get().strip(),
                    "sound":        w["sound"].get().strip(),
                    "sound_repeat": max(1, repeat),
                })
        popups.extend(self._milestone_manager.collect_milestones())
        popups.append(self._milestone_manager.collect_cycle_end())

        return {
            "work_time_min":  work_min,
            "work_time_sec":  work_sec,
            "popup_opacity":  max(10, min(100, self.var_opacity.get())),
            "test_mode":      self.var_test.get(),
            "cycle_align":    self.var_cycle_align.get(),
            "font_name":      self.var_font.get().strip(),
            "message_color":  self.var_color.get().strip(),
            "popups":         popups,
        }

    def _save(self):
        cfg = self._collect()
        if cfg is None:
            return
        if save_config(cfg):
            self.cfg = cfg
            messagebox.showinfo("Saved",
                                f"Configuration saved to:\n{CONFIG_PATH}\n\n"
                                "Restart EyeGuard for changes to take effect.")

    def _reset(self):
        if messagebox.askyesno("Reset", "Reset all settings to defaults?"):
            self.cfg = json.loads(json.dumps(DEFAULT_CONFIG))
            self._populate()


# ====================== ENTRY ======================

if __name__ == "__main__":
    app = ConfigApp()
    app.mainloop()
import time
import tkinter as tk
from tkinter import Toplevel
from PIL import Image, ImageTk
import pygame
import ctypes
import os
import sys
import threading
import json
from queue import Queue

# ── Windows session / power event constants ───────────────────────────────────
# Used to detect lock/unlock and sleep/wake so the On-Start popup can fire.
try:
    import ctypes.wintypes as _wintypes
    _WTSAPI32     = ctypes.windll.WtsApi32
    _USER32       = ctypes.windll.user32
    _WTS_NOTIFY   = True
except Exception:
    _WTS_NOTIFY   = False

# Session-change notification codes (WM_WTSSESSION_CHANGE wParam)
WTS_SESSION_LOCK       = 0x7
WTS_SESSION_UNLOCK     = 0x8
WM_WTSSESSION_CHANGE   = 0x02B1

# Power-broadcast event codes (WM_POWERBROADCAST wParam)
PBT_APMRESUMESUSPEND      = 0x0007   # resume from suspend (user present)
PBT_APMRESUMEAUTOMATIC    = 0x0012   # resume from suspend (automatic)
WM_POWERBROADCAST         = 0x0218

# ====================== BASE PATH ======================
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ====================== LOAD CONFIG ======================
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "config.json")

DEFAULT_CONFIG = {
    "work_time_min":  24,
    "work_time_sec":   0,
    "popup_opacity": 100,
    "test_mode":   False,
    "cycle_align":  True,
    "font_name":   "Montserrat",
    "message_color": "#222222",
    "popups": [
        {
            "trigger": "start",
            "message": "EyeGuard is now active \u2014 helping you care for your eyes!",
            "image": "1.png",
            "sound": "sound_01.mp3",
            "sound_repeat": 1
        },
        {
            "trigger": "work_end",
            "message": "Your eyes deserve a quick rest. Take a 30-second break!",
            "image": "2.png",
            "sound": "sound_04.mp3",
            "sound_repeat": 1
        },
        {
            "trigger": "break_end",
            "message": "Let AI help \u2014 build, test, commit!",
            "image": "3.png",
            "sound": "sound_09.mp3",
            "sound_repeat": 1,
            "duration_min": 3,
            "duration_sec": 0
        },
        {
            "trigger": "break_end",
            "message": "Your eyes deserve a quick rest. Take a 60-second break!",
            "image": "2.png",
            "sound": "sound_05.mp3",
            "sound_repeat": 2,
            "duration_min": 1,
            "duration_sec": 0
        },
        {
            "trigger": "break_end",
            "message": "You\u2019re refreshed now! Go enjoy your life!",
            "image": "1.png",
            "sound": "sound_10.mp3",
            "sound_repeat": 3,
            "duration_min": 2,
            "duration_sec": 0
        },
        {
            "trigger": "break_end",
            "message": "Great! Let\u2019s get back to it, refreshed and focused!",
            "image": "4.png",
            "sound": "sound_06.mp3",
            "sound_repeat": 3,
            "duration_min": 0,
            "duration_sec": 0
        }
    ]
}

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            cfg = DEFAULT_CONFIG.copy()
            cfg.update(user_cfg)
            return cfg
        except Exception as e:
            print(f"[CONFIG] Failed to load config.json, using defaults: {e}")
    return DEFAULT_CONFIG.copy()

CONFIG = load_config()

# ====================== CONFIGURATION ======================
MESSAGE_COLOR  = CONFIG.get("message_color", "#222222")
FONT_NAME      = CONFIG.get("font_name", "Montserrat")

_opacity_pct   = CONFIG.get("popup_opacity", 100)
POPUP_ALPHA    = max(0.10, min(1.0, _opacity_pct / 100.0))

ICON_PATH      = os.path.join(BASE_DIR, "assets", "media", "icons", "icon.ico")
FIGURES_DIR    = os.path.join(BASE_DIR, "assets", "media", "figures")
SOUNDS_DIR     = os.path.join(BASE_DIR, "assets", "media", "sounds")

TEST_MODE      = CONFIG.get("test_mode", False)
TEST_INTERVAL  = 5   # seconds per interval in test mode

if TEST_MODE:
    WORK_TIME = TEST_INTERVAL
else:
    WORK_TIME = (CONFIG.get("work_time_min", 25) * 60
                 + CONFIG.get("work_time_sec", 0))

BREAK_MILESTONES = [
    p for p in CONFIG.get("popups", [])
    if p.get("trigger") == "break_end"
]

if TEST_MODE:
    MILESTONE_DURATIONS = [TEST_INTERVAL] * len(BREAK_MILESTONES)
else:
    MILESTONE_DURATIONS = [
        p.get("duration_min", 0) * 60 + p.get("duration_sec", 0)
        for p in BREAK_MILESTONES
    ]

BREAK_TIME  = sum(MILESTONE_DURATIONS)
TOTAL_CYCLE = WORK_TIME + BREAK_TIME

# ──────────────────────────────────────────────────────────────────────────────
# NEW POPUP SEQUENCE (popup fires first, then its duration elapses):
#
#   cycle_start
#   │
#   ├── work phase begins SILENTLY (no popup, no sound — the Cycle End
#   │   popup that just fired is the only thing the user sees/hears)
#   │   sleep WORK_TIME
#   │
#   ├── fire milestone[0] popup                    ← break phase begins
#   │   sleep MILESTONE_DURATIONS[0]
#   │
#   ├── fire milestone[1] popup
#   │   sleep MILESTONE_DURATIONS[1]
#   │
#   └── (repeat for all milestones)
#       → next cycle starts (silently — see above)
#
# The "start" popup is the APP-START notice only (launch / unlock / wake).
# It is never part of the cycle.
#
# TOTAL_CYCLE = WORK_TIME + sum(MILESTONE_DURATIONS)   [unchanged]
# ──────────────────────────────────────────────────────────────────────────────

CYCLE_ALIGN = CONFIG.get("cycle_align", False) and not TEST_MODE

POPUPS = CONFIG.get("popups", DEFAULT_CONFIG["popups"])

def get_popup_by_trigger(trigger):
    for p in POPUPS:
        if p.get("trigger") == trigger:
            return p
    return None

pygame.init()
pygame.mixer.init()

def play_sound_async(sound_filename, repeat=1):
    sound_path = os.path.join(SOUNDS_DIR, sound_filename)
    def _play():
        for _ in range(repeat):
            if os.path.exists(sound_path):
                pygame.mixer.music.load(sound_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            else:
                print(f"[SOUND] File not found: {sound_path}")
    threading.Thread(target=_play, daemon=True).start()

popup_queue = Queue()
DISPLAY_TIME  = 3000

def fade_in(popup, target_alpha, step=0.0):
    if step <= target_alpha:
        popup.attributes("-alpha", step)
        popup.after(20, lambda: fade_in(popup, target_alpha, step + 0.05))
    else:
        popup.attributes("-alpha", target_alpha)

def fade_out(popup, step=None):
    if step is None:
        step = POPUP_ALPHA
    if step >= 0.0:
        popup.attributes("-alpha", step)
        popup.after(20, lambda: fade_out(popup, step - 0.05))
    else:
        popup.attributes("-alpha", 0.0)
        popup.destroy()

def create_popup(root, message, image_path):
    popup = Toplevel(root)
    popup.overrideredirect(True)
    popup.attributes("-topmost", True)
    popup.attributes("-alpha", 0.0)

    user32 = ctypes.windll.user32
    screen_width  = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
    popup_width   = 420
    popup_height  = 160
    x = screen_width  - popup_width  - 20
    y = screen_height - popup_height - 60
    popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")

    outer_frame = tk.Frame(popup, bg="black", bd=0)
    outer_frame.pack(fill="both", expand=True)

    container = tk.Frame(outer_frame, bg="white", padx=10, pady=10)
    container.pack(fill="both", expand=True)

    header = tk.Frame(container, bg="white")
    header.pack(fill="x", pady=(0, 0))

    if os.path.exists(ICON_PATH):
        icon       = Image.open(ICON_PATH).resize((20, 20))
        icon_photo = ImageTk.PhotoImage(icon)
        popup.icon_photo = icon_photo
        tk.Label(header, image=icon_photo, bg="white").pack(side="left", padx=(5, 5))

    tk.Label(header, text="EyeGuard", font=(FONT_NAME, 10),
             bg="white", fg=MESSAGE_COLOR).pack(side="left")

    tk.Frame(container, height=1, bg="#dddddd").pack(fill="x", pady=(2, 5))

    content = tk.Frame(container, bg="white")
    content.pack(fill="both", expand=True)

    if image_path and os.path.exists(image_path):
        img   = Image.open(image_path).resize((60, 60))
        photo = ImageTk.PhotoImage(img)
        popup.photo = photo
        tk.Label(content, image=photo, bg="white").pack(side="left", padx=10)

    tk.Label(content, text=message, font=(FONT_NAME, 12),
             bg="white", fg=MESSAGE_COLOR,
             wraplength=280, justify="center").pack(side="left", fill="both", expand=True)

    tk.Label(container,
             text="Developed by Ivan Sicaja © 2026. All rights reserved.",
             font=(FONT_NAME, 8), bg="white", fg="#555555"
             ).pack(side="bottom", pady=(5, 0))

    fade_in(popup, POPUP_ALPHA)
    popup.after(DISPLAY_TIME + 1000, lambda: fade_out(popup, POPUP_ALPHA))

def show_popup(message, image_filename):
    image_path = os.path.join(FIGURES_DIR, image_filename) if image_filename else None
    popup_queue.put((message, image_path))

def check_popup_queue(root):
    try:
        while not popup_queue.empty():
            message, image_path = popup_queue.get_nowait()
            create_popup(root, message, image_path)
    except:
        pass
    root.after(100, lambda: check_popup_queue(root))

def format_time_from_timestamp(timestamp):
    return time.strftime('%H:%M:%S', time.localtime(timestamp)) + f".{int(timestamp % 1 * 1000):03d}"

def fire_popup(trigger=None, popup_data=None):
    """Fire a popup either by trigger name or by passing a popup dict directly."""
    if popup_data is None and trigger is not None:
        popup_data = get_popup_by_trigger(trigger)
    if popup_data:
        show_popup(popup_data.get("message", ""), popup_data.get("image", ""))
        play_sound_async(
            popup_data.get("sound", "sound.mp3"),
            popup_data.get("sound_repeat", 1)
        )

def seconds_since_midnight():
    t = time.localtime()
    return t.tm_hour * 3600 + t.tm_min * 60 + t.tm_sec

def find_aligned_cycle_start_wall():
    """
    With the new popup-first model the "boundary" is still the point where the
    last milestone popup FIRED (not ended).  The grid is the same: multiples of
    TOTAL_CYCLE anchored to midnight.

    We find the NEXT boundary that is at least 1 second in the future, then
    work out where the cycle START must have been so that the last milestone
    fires exactly on that boundary.

    Returns (cycle_start_wall, last_milestone_fire_wall).
    """
    import math

    now_wall = time.time()
    now_sm   = seconds_since_midnight()
    midnight_wall = now_wall - now_sm

    candidate_idx  = math.ceil(now_sm / TOTAL_CYCLE)
    boundary_sm    = candidate_idx * TOTAL_CYCLE
    boundary_wall  = midnight_wall + boundary_sm

    if boundary_wall <= now_wall + 1:
        candidate_idx += 1
        boundary_sm    = candidate_idx * TOTAL_CYCLE
        boundary_wall  = midnight_wall + boundary_sm

    # In the new model:
    #   cycle_start → fire work_end → sleep WORK_TIME
    #               → fire milestone[0] → sleep DUR[0]
    #               → fire milestone[1] → sleep DUR[1]
    #               → ...
    #               → fire milestone[-1]   ← this is the boundary
    #
    # So:  boundary = cycle_start + WORK_TIME + sum(DUR[:-1])
    # i.e. boundary = cycle_start + TOTAL_CYCLE - MILESTONE_DURATIONS[-1]
    #
    # Wait — for alignment we snap the LAST milestone FIRE to the boundary,
    # not the end of the cycle.  The "end of cycle" is boundary + last_dur.
    # But conventionally the user expects "snaps to :00/:30 clock marks",
    # meaning the *work_end* popup fires on those marks (start of break).
    # We keep the same convention: the last milestone *fires* on the boundary,
    # which is the same as before.
    last_fire_wall   = boundary_wall
    cycle_start_wall = last_fire_wall - WORK_TIME - sum(MILESTONE_DURATIONS[:-1])

    return cycle_start_wall, last_fire_wall

def fmt_wall(wall_time):
    return time.strftime('%H:%M:%S', time.localtime(wall_time))

def _precise_sleep(target_perf):
    """Sleep until time.perf_counter() reaches target_perf, using sub-0.5 s slices."""
    while True:
        rem = target_perf - time.perf_counter()
        if rem <= 0:
            break
        time.sleep(min(rem, 0.5))

def timer_thread():
    mode = "TEST" if TEST_MODE else "PRODUCTION"
    print(f"=== EyeGuard Starting in {mode} MODE ===")
    if TEST_MODE:
        print(f"[TEST] Every interval fixed at exactly {TEST_INTERVAL}s")
        print(f"[TEST] Work: {WORK_TIME}s | "
              f"Milestones: {len(BREAK_MILESTONES)} × {TEST_INTERVAL}s each | "
              f"Break total: {BREAK_TIME}s | Cycle total: {TOTAL_CYCLE}s")
    else:
        durations_str = " + ".join(f"{d}s" for d in MILESTONE_DURATIONS)
        print(f"Work: {WORK_TIME}s | Break: {BREAK_TIME}s "
              f"({len(BREAK_MILESTONES)} milestones: {durations_str}) | "
              f"Total: {TOTAL_CYCLE}s")
    print(f"Popup opacity: {_opacity_pct}%")
    print(f"Cycle alignment: {'ON' if CYCLE_ALIGN else 'OFF'}")
    print()
    print("NEW SEQUENCE per cycle:")
    print("  work phase (silent) → sleep WORK_TIME")
    for i, dur in enumerate(MILESTONE_DURATIONS):
        print(f"  fire milestone[{i+1}] popup → sleep {dur}s")
    print("=" * 60)

    # ── App-start popup fires once immediately on launch ──────────────
    # (informational only: tells the user EyeGuard is running)
    fire_popup("start")

    # ──────────────────────────────────────────────────────────────────
    # ALIGNED FIRST CYCLE
    # ──────────────────────────────────────────────────────────────────
    if CYCLE_ALIGN:
        cycle_start_wall, last_fire_wall = find_aligned_cycle_start_wall()
        now_wall = time.time()

        # Derive absolute wall-clock fire times for every event:
        #   work_end fires at: cycle_start_wall  (first event of cycle)
        #   milestone[i] fires at: cycle_start_wall + WORK_TIME + sum(DUR[:i])
        work_end_fire_wall = cycle_start_wall
        milestone_fire_walls = []
        t = cycle_start_wall + WORK_TIME
        for dur in MILESTONE_DURATIONS:
            milestone_fire_walls.append(t)
            t += dur

        print(f"\n[ALIGN] Last milestone fires at: {fmt_wall(last_fire_wall)}")
        print(f"[ALIGN] Aligned cycle start:     {fmt_wall(cycle_start_wall)}")
        print(f"[ALIGN] Work End fires at:        {fmt_wall(work_end_fire_wall)}")
        for i, fw in enumerate(milestone_fire_walls):
            print(f"[ALIGN] Milestone {i+1} fires at:  {fmt_wall(fw)}")

        # ── Work End popup (may fire immediately if already past target) ──
        if work_end_fire_wall > now_wall:
            wait   = work_end_fire_wall - now_wall
            end_pc = time.perf_counter() + wait
            print(f"[ALIGN] Waiting {wait:.1f}s for Work End at {fmt_wall(work_end_fire_wall)}")
            _precise_sleep(end_pc)

        # Work phase starts silently — no popup/sound here, so nothing can
        # overlap the App-Start or Cycle End popups.
        print(f"[WORK PHASE START] {format_time_from_timestamp(time.time())} "
              f"(target {fmt_wall(work_end_fire_wall)})")

        # ── Milestone popups ─────────────────────────────────────────
        for idx, (milestone, fire_wall) in enumerate(
                zip(BREAK_MILESTONES, milestone_fire_walls)):
            now_wall = time.time()
            if fire_wall > now_wall:
                end_pc = time.perf_counter() + (fire_wall - now_wall)
                _precise_sleep(end_pc)

            drift = time.time() - fire_wall
            print(f"[MILESTONE {idx+1} POPUP] {format_time_from_timestamp(time.time())} "
                  f"(target {fmt_wall(fire_wall)} | drift {drift:+.3f}s)")
            fire_popup(popup_data=milestone)

        # After aligned first cycle the next cycle starts after the last
        # milestone's duration has elapsed (= last_fire_wall + last_dur)
        last_dur = MILESTONE_DURATIONS[-1] if MILESTONE_DURATIONS else 0
        next_cycle_start_wall = last_fire_wall + last_dur
        print(f"[ALIGN] Aligned cycle complete. "
              f"Next cycle starts at {fmt_wall(next_cycle_start_wall)}")

        # Sleep until the next cycle boundary
        gap = next_cycle_start_wall - time.time()
        if gap > 0:
            _precise_sleep(time.perf_counter() + gap)

        cycle_number = 2
    else:
        cycle_number = 1

    # ──────────────────────────────────────────────────────────────────
    # NORMAL CYCLE LOOP
    # ──────────────────────────────────────────────────────────────────
    while True:
        cycle_start_pc  = time.perf_counter()
        cycle_start_wall = time.time()
        print(f"\n[CYCLE {cycle_number} START] {format_time_from_timestamp(cycle_start_wall)}")

        # ── 1. Work phase begins silently ─────────────────────────────
        # No popup and no sound here: the Cycle End popup (last break
        # milestone, 0 s duration) fires at this exact moment, and it must
        # be the ONLY thing the user sees and hears at the end of a cycle.
        print(f"[WORK PHASE START] {format_time_from_timestamp(time.time())} | "
              f"work phase begins ({WORK_TIME}s)")

        # ── 2. Sleep for the full work duration ──────────────────────
        work_target_pc = cycle_start_pc + WORK_TIME
        _precise_sleep(work_target_pc)

        elapsed = time.perf_counter() - cycle_start_pc
        drift   = elapsed - WORK_TIME
        print(f"[WORK END  SLEEP] {format_time_from_timestamp(time.time())} | "
              f"expected +{WORK_TIME:.3f}s | actual +{elapsed:.3f}s | drift {drift:+.6f}s")

        # ── 3. Fire each milestone popup then sleep its duration ──────
        accum = WORK_TIME
        for idx, (milestone, dur) in enumerate(
                zip(BREAK_MILESTONES, MILESTONE_DURATIONS)):

            ms_fire_pc = time.perf_counter()
            elapsed_at_fire = ms_fire_pc - cycle_start_pc
            print(f"[MILESTONE {idx+1} POPUP] {format_time_from_timestamp(time.time())} | "
                  f"break phase {idx+1} begins ({dur}s) | "
                  f"cycle elapsed +{elapsed_at_fire:.3f}s")
            fire_popup(popup_data=milestone)

            accum         += dur
            ms_target_pc   = cycle_start_pc + accum
            _precise_sleep(ms_target_pc)

            elapsed = time.perf_counter() - cycle_start_pc
            drift   = elapsed - accum
            print(f"[MILESTONE {idx+1} SLEEP] {format_time_from_timestamp(time.time())} | "
                  f"expected +{accum:.3f}s | actual +{elapsed:.3f}s | drift {drift:+.6f}s")

        # ── 4. Cycle summary ─────────────────────────────────────────
        cycle_elapsed = time.perf_counter() - cycle_start_pc
        cycle_drift   = cycle_elapsed - TOTAL_CYCLE
        print(f"[CYCLE {cycle_number} END]  "
              f"{format_time_from_timestamp(time.time())} | "
              f"expected {TOTAL_CYCLE:.3f}s | actual {cycle_elapsed:.3f}s | "
              f"total drift {cycle_drift:+.6f}s")
        cycle_number += 1

def main():
    root = tk.Tk()
    root.withdraw()
    check_popup_queue(root)
    threading.Thread(target=timer_thread, daemon=True).start()

    # ── Register for Windows session-change and power notifications ───────────
    # This lets the On-Start popup fire when the PC is unlocked or wakes from
    # sleep/hibernate, without touching the timer cycle at all.
    if _WTS_NOTIFY:
        _register_session_notifications(root)

    root.mainloop()


# ── Windows session / power notification hook ─────────────────────────────────

def _register_session_notifications(root):
    """
    Subclass the hidden Tk root HWND to intercept WM_WTSSESSION_CHANGE and
    WM_POWERBROADCAST messages.  When the session is unlocked or the machine
    resumes from sleep, fire the On-Start popup once.

    Safe to call on any version of Windows; silently does nothing if the
    required APIs are not available.
    """
    try:
        import ctypes
        import ctypes.wintypes as wt

        # Give the hidden Tk window a moment to get an HWND
        def _setup():
            try:
                hwnd = root.winfo_id()

                # Register for session-change notifications
                ctypes.windll.WtsApi32.WTSRegisterSessionNotification(hwnd, 0)

                # Subclass the window proc
                WndProcType = ctypes.WINFUNCTYPE(
                    ctypes.c_long,          # return type
                    wt.HWND,
                    wt.UINT,
                    wt.WPARAM,
                    wt.LPARAM,
                )

                # Keep a reference so GC never kills the callback
                root._old_wnd_proc = ctypes.windll.user32.GetWindowLongPtrW(hwnd, -4)

                def _wnd_proc(hwnd_, msg, wparam, lparam):
                    if msg == WM_WTSSESSION_CHANGE:
                        if wparam == WTS_SESSION_UNLOCK:
                            print("[SESSION] Unlock detected — firing App-Start popup")
                            fire_popup("start")
                    elif msg == WM_POWERBROADCAST:
                        if wparam in (PBT_APMRESUMESUSPEND, PBT_APMRESUMEAUTOMATIC):
                            print("[POWER] Resume from sleep detected — firing App-Start popup")
                            fire_popup("start")
                    # Call the original window proc
                    return ctypes.windll.user32.CallWindowProcW(
                        root._old_wnd_proc, hwnd_, msg, wparam, lparam)

                root._wnd_proc_ref = WndProcType(_wnd_proc)
                ctypes.windll.user32.SetWindowLongPtrW(
                    hwnd, -4, root._wnd_proc_ref)

                print("[SESSION] Windows session/power notifications registered")
            except Exception as e:
                print(f"[SESSION] Could not register notifications: {e}")

        # Delay slightly so Tk has fully created the window
        root.after(500, _setup)

    except Exception as e:
        print(f"[SESSION] Notification setup skipped: {e}")

if __name__ == "__main__":
    main()
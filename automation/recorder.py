"""Click and scroll recorder/replayer for MacroFactor automation.

Since MacroFactor runs as a fixed-size "Designed for iPhone" window,
UI elements are always at the same position relative to the window.

Records clicks AND scrolls. Replays them with configurable speed.

Usage:
  Record:  macroclaw auto record daily
  Replay:  macroclaw auto daily
"""

import json
import logging
import subprocess
import time
from pathlib import Path

import pyautogui

logger = logging.getLogger("macroclaw.recorder")

SEQUENCES_DIR = Path(__file__).parent.parent / "data" / "sequences"


def get_app_window_position(app_name: str = "MacroFactor") -> tuple[int, int, int, int]:
    """Get the app window bounds (x, y, width, height) via AppleScript."""
    script = f'''
    tell application "System Events"
        tell process "{app_name}"
            set frontWindow to first window
            set {{x, y}} to position of frontWindow
            set {{w, h}} to size of frontWindow
        end tell
    end tell
    return (x as text) & " " & (y as text) & " " & (w as text) & " " & (h as text)
    '''
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Could not get window position: {result.stderr.strip()}")

    parts = result.stdout.strip().split()
    return int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])


def record_sequence(name: str, app_name: str = "MacroFactor") -> Path:
    """Record clicks and scrolls interactively.

    Opens the app, then listens for mouse clicks and scroll events.
    Positions are saved relative to the app window.
    Press Ctrl+C to stop recording.
    """
    from pynput import mouse

    subprocess.run(["open", "-a", app_name], check=True)
    time.sleep(3)

    wx, wy, ww, wh = get_app_window_position(app_name)
    print(f"App window: ({wx}, {wy}) {ww}x{wh}")
    print()
    print("Click and scroll through the export flow in MacroFactor.")
    print("Clicks and scrolls inside the app window will be recorded.")
    print("Press Ctrl+C when done.")
    print()

    steps: list[dict] = []
    last_event_time = [time.time()]  # mutable container for closure access

    def _in_window(x, y):
        return 0 <= (x - wx) <= ww and 0 <= (y - wy) <= wh

    def _elapsed():
        now = time.time()
        delay = max(0.3, now - last_event_time[0])
        last_event_time[0] = now
        return round(delay, 2)

    def on_click(x, y, button, pressed):
        if not pressed:
            return
        if _in_window(x, y):
            rel_x = x - wx
            rel_y = y - wy
            delay = _elapsed()
            step = {
                "type": "click",
                "rel_x": rel_x,
                "rel_y": rel_y,
                "delay_before": delay,
                "description": f"Step {len(steps) + 1}: click ({rel_x:.0f}, {rel_y:.0f})",
            }
            steps.append(step)
            print(f"  Click: ({rel_x:.0f}, {rel_y:.0f}) delay={delay}s — step {len(steps)}")
        else:
            print(f"  (outside app window, ignored)")

    def on_scroll(x, y, dx, dy):
        if _in_window(x, y):
            rel_x = x - wx
            rel_y = y - wy
            delay = _elapsed()
            step = {
                "type": "scroll",
                "rel_x": rel_x,
                "rel_y": rel_y,
                "dx": dx,
                "dy": dy,
                "delay_before": delay,
                "description": f"Step {len(steps) + 1}: scroll dy={dy}",
            }
            steps.append(step)
            print(f"  Scroll: dy={dy} at ({rel_x:.0f}, {rel_y:.0f}) delay={delay}s — step {len(steps)}")

    listener = mouse.Listener(on_click=on_click, on_scroll=on_scroll)
    listener.start()

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()

    if not steps:
        print("No events recorded.")
        return None

    # Collapse consecutive scroll events at similar positions into one
    collapsed = _collapse_scrolls(steps)

    SEQUENCES_DIR.mkdir(parents=True, exist_ok=True)
    path = SEQUENCES_DIR / f"{name}.json"
    data = {
        "name": name,
        "app_name": app_name,
        "window_size": {"width": ww, "height": wh},
        "steps": collapsed,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    path.write_text(json.dumps(data, indent=2))
    print(f"\nSaved {len(collapsed)} steps to {path}")
    return path


def _collapse_scrolls(steps: list[dict]) -> list[dict]:
    """Merge consecutive scroll events into single scroll steps."""
    if not steps:
        return steps

    collapsed = [steps[0]]
    for step in steps[1:]:
        prev = collapsed[-1]
        if step["type"] == "scroll" and prev["type"] == "scroll":
            # Merge: accumulate dy, keep position of first
            prev["dy"] = prev.get("dy", 0) + step.get("dy", 0)
            prev["dx"] = prev.get("dx", 0) + step.get("dx", 0)
            prev["description"] = f"Scroll dy={prev['dy']}"
        else:
            collapsed.append(step)
    return collapsed


def replay_sequence(name: str, app_name: str = "MacroFactor", speed: float = 1.0) -> None:
    """Replay a recorded click/scroll sequence.

    Opens the app, gets the current window position, and replays
    all events at the recorded relative positions.
    """
    path = SEQUENCES_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No recorded sequence '{name}'. Run: macroclaw auto record {name}"
        )

    data = json.loads(path.read_text())
    steps = data["steps"]
    logger.info("Replaying '%s' (%d steps)", name, len(steps))

    # Force-kill and reopen to ensure clean state (home screen)
    # iOS "Designed for iPhone" apps run as "Runner" on macOS
    subprocess.run(["osascript", "-e", f'tell application "{app_name}" to quit'], capture_output=True)
    time.sleep(1)
    subprocess.run(["pkill", "-x", "Runner"], capture_output=True)
    time.sleep(1)
    subprocess.run(["open", "-a", app_name], check=True)
    time.sleep(4)

    # Bring window to front and focus it
    focus_script = f'''
    tell application "System Events"
        tell process "{app_name}"
            set frontmost to true
        end tell
    end tell
    '''
    subprocess.run(["osascript", "-e", focus_script], capture_output=True)
    time.sleep(0.5)

    wx, wy, ww, wh = get_app_window_position(app_name)
    logger.info("App window: (%d, %d) %dx%d", wx, wy, ww, wh)

    # Click center of window first to ensure focus
    pyautogui.click(wx + ww // 2, wy + wh // 2)
    time.sleep(1)

    rec_w = data.get("window_size", {}).get("width", 0)
    rec_h = data.get("window_size", {}).get("height", 0)
    if rec_w and rec_h and (rec_w != ww or rec_h != wh):
        logger.warning(
            "Window size changed: recorded %dx%d, now %dx%d. Clicks may be offset.",
            rec_w, rec_h, ww, wh,
        )

    for i, step in enumerate(steps):
        delay = step.get("delay_before", 1.5) * speed
        time.sleep(delay)

        abs_x = wx + int(step["rel_x"])
        abs_y = wy + int(step["rel_y"])
        action = step.get("type", "click")
        desc = step.get("description", f"Step {i+1}")

        if action == "click":
            logger.info("  %s -> click (%d, %d) [waited %.1fs]", desc, abs_x, abs_y, delay)
            pyautogui.moveTo(abs_x, abs_y, duration=0.15)
            time.sleep(0.1)
            pyautogui.click()
        elif action == "scroll":
            dy = step.get("dy", 0)
            logger.info("  %s -> scroll dy=%d at (%d, %d) [waited %.1fs]", desc, dy, abs_x, abs_y, delay)
            pyautogui.moveTo(abs_x, abs_y, duration=0.1)
            # Send scroll in one go — then wait for momentum to settle
            pyautogui.scroll(dy)
            time.sleep(1.0)

    logger.info("Replay complete.")


def edit_sequence(name: str) -> None:
    """Print sequence steps."""
    path = SEQUENCES_DIR / f"{name}.json"
    if not path.exists():
        print(f"No sequence '{name}' found.")
        return

    data = json.loads(path.read_text())
    print(f"Sequence: {name} ({len(data['steps'])} steps)")
    print(f"Recorded: {data.get('recorded_at', 'unknown')}")
    print(f"Window: {data.get('window_size', {})}")
    print()
    for i, step in enumerate(data["steps"]):
        action = step.get("type", "click")
        if action == "scroll":
            print(f"  {i+1}. SCROLL dy={step.get('dy', 0)} at ({step['rel_x']:.0f}, {step['rel_y']:.0f}) delay={step['delay_before']}s")
        else:
            print(f"  {i+1}. CLICK ({step['rel_x']:.0f}, {step['rel_y']:.0f}) delay={step['delay_before']}s — {step.get('description', '')}")

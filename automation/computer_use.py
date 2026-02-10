"""Claude Computer Use agent for MacroFactor automation.

Uses the Anthropic Computer Use API to visually navigate and control the
MacroFactor app. Claude views screenshots of the app window, decides what
actions to take (click, scroll, type), and we execute those actions via
pyautogui.
"""

import base64
import io
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

import pyautogui

from automation.recorder import get_app_window_position

logger = logging.getLogger("macroclaw.computer_use")

APP_NAME = "MacroFactor"
MAX_ITERATIONS = 50
MAX_HISTORY_SCREENSHOTS = 2

_MODEL_CONFIG = {
    "claude-sonnet-4-5-20250929": {
        "tool_type": "computer_20250124",
        "betas": ["computer-use-2025-01-24"],
    },
    "claude-opus-4-6": {
        "tool_type": "computer_20251124",
        "betas": ["computer-use-2025-11-24"],
    },
}

_MODEL_ALIASES = {
    "claude-sonnet-4-5": "claude-sonnet-4-5-20250929",
    "sonnet": "claude-sonnet-4-5-20250929",
    "claude-opus-4-6": "claude-opus-4-6",
    "opus": "claude-opus-4-6",
}

_SYSTEM_PROMPT = (
    "You are a UI automation bot controlling a macOS app called '{app_name}'. "
    "Screenshots show ONLY the app window ({w}x{h}px). "
    "Coordinates (0,0) = top-left of the window.\n\n"
    "RULES:\n"
    "- Execute actions IMMEDIATELY. Do not explain or narrate.\n"
    "- One action per step. You get a fresh screenshot after every action.\n"
    "- Do NOT use the screenshot action — it is automatic.\n"
    "- Follow the user's numbered steps in exact order.\n"
    "- To scroll, use the scroll action with scroll_direction and scroll_amount.\n"
    "- When done, respond with ONLY text starting with 'DONE:' (no tool use)."
)


def _resolve_model(model: str) -> str:
    return _MODEL_ALIASES.get(model, model)


def _get_tool_config(model: str) -> dict:
    model_id = _resolve_model(model)
    config = _MODEL_CONFIG.get(model_id)
    if not config:
        config = _MODEL_CONFIG["claude-sonnet-4-5-20250929"]
    return config


def _restart_app(app_name: str = APP_NAME) -> None:
    """Kill and reopen the app to ensure a fresh home screen."""
    _log(f"Restarting {app_name}...")
    subprocess.run(
        ["osascript", "-e", f'tell application "{app_name}" to quit'],
        capture_output=True,
    )
    time.sleep(1)
    subprocess.run(["pkill", "-x", "Runner"], capture_output=True)
    time.sleep(1)
    subprocess.run(["open", "-a", app_name], check=True)
    time.sleep(4)
    subprocess.run(
        ["osascript", "-e",
         f'tell application "System Events" to tell process "{app_name}" '
         f'to set frontmost to true'],
        capture_output=True,
    )
    time.sleep(0.5)
    _log(f"{app_name} restarted.")


def _capture_window_screenshot(
    app_name: str = APP_NAME,
) -> tuple[str, tuple[int, int, int, int]]:
    """Capture a JPEG screenshot cropped to the app window."""
    wx, wy, ww, wh = get_app_window_position(app_name)
    screenshot = pyautogui.screenshot(region=(wx, wy, ww, wh)).convert("RGB")

    buf = io.BytesIO()
    screenshot.save(buf, format="JPEG", quality=50)
    b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")

    return b64, (wx, wy, ww, wh)


def _execute_action(
    action: dict[str, Any],
    window_bounds: tuple[int, int, int, int],
) -> None:
    """Execute a Claude computer use action via pyautogui.

    Action formats (from Anthropic reference implementation):
    - left_click: coordinate=[x,y], optional key (modifier)
    - right_click/middle_click/double_click/triple_click: coordinate=[x,y]
    - left_click_drag: start_coordinate=[x,y], coordinate=[x,y] (end)
    - scroll: scroll_direction="up"|"down"|"left"|"right", scroll_amount=int, coordinate=[x,y]
    - type: text="string"
    - key: text="key combo" (e.g. "Return", "ctrl+c")
    - mouse_move: coordinate=[x,y]
    - screenshot: no params (no-op, we auto-capture)
    - wait: duration=seconds
    """
    wx, wy, ww, wh = window_bounds
    action_type = action.get("action")
    coord = action.get("coordinate")

    if coord:
        abs_x = wx + coord[0]
        abs_y = wy + coord[1]
    else:
        abs_x = abs_y = None

    if action_type == "screenshot":
        pass

    elif action_type == "left_click":
        _log(f"  -> click ({coord[0]}, {coord[1]})")
        pyautogui.click(abs_x, abs_y)
        time.sleep(0.5)

    elif action_type == "left_click_drag":
        start = action.get("start_coordinate", coord)
        end = coord
        sx, sy = wx + start[0], wy + start[1]
        ex, ey = wx + end[0], wy + end[1]
        _log(f"  -> drag ({start[0]},{start[1]}) to ({end[0]},{end[1]})")
        pyautogui.moveTo(sx, sy, duration=0.1)
        pyautogui.mouseDown()
        pyautogui.moveTo(ex, ey, duration=0.4)
        pyautogui.mouseUp()
        time.sleep(1.0)

    elif action_type == "right_click":
        _log(f"  -> right-click ({coord[0]}, {coord[1]})")
        pyautogui.rightClick(abs_x, abs_y)
        time.sleep(0.5)

    elif action_type in ("double_click", "triple_click"):
        clicks = 3 if action_type == "triple_click" else 2
        _log(f"  -> {action_type} ({coord[0]}, {coord[1]})")
        pyautogui.click(abs_x, abs_y, clicks=clicks)
        time.sleep(0.5)

    elif action_type == "mouse_move":
        _log(f"  -> move ({coord[0]}, {coord[1]})")
        pyautogui.moveTo(abs_x, abs_y, duration=0.2)

    elif action_type == "scroll":
        direction = action.get("scroll_direction", "down")
        amount = action.get("scroll_amount", 3)
        # Multiply scroll amount — macOS "Designed for iPhone" apps need
        # aggressive scrolling; pyautogui units are tiny.
        pixels = amount * 15
        coord_str = f" at ({coord[0]},{coord[1]})" if coord else ""
        _log(f"  -> scroll {direction} {amount} (px={pixels}){coord_str}")

        if coord:
            pyautogui.moveTo(abs_x, abs_y, duration=0.1)

        if direction == "down":
            pyautogui.scroll(-pixels)
        elif direction == "up":
            pyautogui.scroll(pixels)
        elif direction == "left":
            pyautogui.hscroll(-pixels)
        elif direction == "right":
            pyautogui.hscroll(pixels)
        time.sleep(1.0)

    elif action_type == "type":
        text = action.get("text", "")
        _log(f"  -> type '{text[:50]}'")
        pyautogui.write(text, interval=0.03)
        time.sleep(0.3)

    elif action_type == "key":
        # Key action uses 'text' field per Anthropic reference impl
        text = action.get("text", "")
        _log(f"  -> key '{text}'")
        if text:
            # Handle combos like "ctrl+c" and single keys like "Return"
            keys = text.split("+")
            pyautogui.hotkey(*keys)
        time.sleep(0.3)

    elif action_type == "wait":
        duration = action.get("duration", 2)
        _log(f"  -> wait {duration}s")
        time.sleep(duration)

    elif action_type in ("left_mouse_down", "left_mouse_up"):
        _log(f"  -> {action_type}")
        if action_type == "left_mouse_down":
            pyautogui.mouseDown()
        else:
            pyautogui.mouseUp()
        time.sleep(0.3)

    elif action_type == "hold_key":
        text = action.get("text", "")
        duration = action.get("duration", 1)
        _log(f"  -> hold_key '{text}' for {duration}s")
        if text:
            pyautogui.keyDown(text)
            time.sleep(duration)
            pyautogui.keyUp(text)

    else:
        _log(f"  -> UNKNOWN: {action_type} (raw: {action})")


def _build_tool_result(
    tool_use_id: str,
    app_name: str = APP_NAME,
) -> tuple[dict, tuple[int, int, int, int]]:
    """Build a tool_result with a fresh JPEG screenshot."""
    b64, bounds = _capture_window_screenshot(app_name)
    result = {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": b64,
                },
            }
        ],
    }
    return result, bounds


def _trim_messages(messages: list[dict], keep_first: int = 1) -> list[dict]:
    """Keep first message + last N exchanges to limit token growth."""
    if len(messages) <= keep_first + MAX_HISTORY_SCREENSHOTS * 2:
        return messages
    head = messages[:keep_first]
    tail = messages[-(MAX_HISTORY_SCREENSHOTS * 2):]
    return head + tail


def agent_loop(
    instruction: str,
    model: str = "claude-sonnet-4-5",
    max_iterations: int = MAX_ITERATIONS,
    app_name: str = APP_NAME,
    restart: bool = False,
    callback: Callable[[int, str, dict | None], None] | None = None,
) -> str:
    """Run the computer use agent loop."""
    import anthropic

    model_id = _resolve_model(model)
    config = _get_tool_config(model)
    client = anthropic.Anthropic(max_retries=5)

    if restart:
        _restart_app(app_name)
    else:
        from automation.app import focus_app
        focus_app(app_name)
        time.sleep(1.0)

    b64, bounds = _capture_window_screenshot(app_name)

    tool_def = {
        "type": config["tool_type"],
        "name": "computer",
        "display_width_px": bounds[2],
        "display_height_px": bounds[3],
    }

    system_prompt = _SYSTEM_PROMPT.format(
        app_name=app_name, w=bounds[2], h=bounds[3]
    )

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": b64,
                    },
                },
                {"type": "text", "text": instruction},
            ],
        }
    ]

    final_text = ""

    for iteration in range(1, max_iterations + 1):
        if iteration > 1:
            time.sleep(3)  # pace requests to stay under rate limits

        if callback:
            callback(iteration, "api_call", None)

        _log(f"[{iteration}/{max_iterations}] API call...")

        trimmed = _trim_messages(messages)

        response = client.beta.messages.create(
            model=model_id,
            max_tokens=1024,
            system=system_prompt,
            tools=[tool_def],
            messages=trimmed,
            betas=config["betas"],
        )

        text_blocks = [block.text for block in response.content if block.type == "text"]
        if text_blocks:
            final_text = "\n".join(text_blocks)
            _log(f"  Claude: {final_text}")

        has_tool_use = any(block.type == "tool_use" for block in response.content)
        if not has_tool_use:
            _log("DONE.")
            if callback:
                callback(iteration, "done", {"text": final_text})
            return final_text

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            action = block.input
            action_type = action.get("action", "unknown")

            if callback:
                callback(iteration, "action", {"action": action_type, "input": action})

            try:
                bounds = get_app_window_position(app_name)
            except RuntimeError:
                pass

            _execute_action(action, bounds)
            result, bounds = _build_tool_result(block.id, app_name)
            tool_results.append(result)

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    _log(f"Max iterations ({max_iterations}) reached.")
    return final_text or "(max iterations reached)"


def run_export_with_agent(
    export_type: str,
    model: str = "claude-sonnet-4-5",
    download_timeout: float = 30.0,
    app_name: str = APP_NAME,
) -> Path:
    """Kill/reopen MacroFactor, run the AI export flow, handle download."""
    from automation.export import _move_to_imports, _wait_for_download

    instruction = (
        "Export my MacroFactor data. Execute these steps IN ORDER:\n"
        "1. Tap 'More' (bottom-right nav bar).\n"
        "2. Scroll down to 'Data Management'. Tap 'Data Export'.\n"
        "3. Tap 'Granular Export' at the top.\n"
        "4. METRICS & ANALYTICS section: if button says 'Select All' → tap it. "
        "If 'Deselect All' → already selected, skip.\n"
        "5. Scroll down to reveal the 'Library' section.\n"
        "6. LIBRARY section: if 'Select All' → tap it. If 'Deselect All' → skip.\n"
        "7. Scroll down to reveal the 'Other' section.\n"
        "8. OTHER section: if 'Select All' → tap it. If 'Deselect All' → skip.\n"
        "9. Scroll down. Tap the 'Export' button.\n"
        "10. Popup appears → tap 'Save'.\n"
        "11. Save to Downloads → tap 'Save'.\n"
        "DONE after final Save."
    )

    start = time.time()
    _log("=" * 50)
    _log(f"{export_type.upper()} EXPORT — AI agent mode")
    _log("=" * 50)

    try:
        agent_loop(instruction, model=model, app_name=app_name, restart=True)
        downloaded = _wait_for_download(timeout=download_timeout)
        imported = _move_to_imports(downloaded)
        _log(f"{export_type.upper()} EXPORT — done in {time.time() - start:.1f}s -> {imported}")
        return imported
    except Exception:
        _log(f"{export_type.upper()} EXPORT — FAILED after {time.time() - start:.1f}s")
        raise


def _log(msg: str) -> None:
    logger.info(msg)
    print(msg, file=sys.stderr, flush=True)

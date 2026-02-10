"""MacroFactor app management — launch, focus, close."""

import logging
import subprocess
import time

logger = logging.getLogger("macroclaw.app")

APP_NAME = "MacroFactor"


def is_running(app_name: str = APP_NAME) -> bool:
    """Check if the app is currently running."""
    result = subprocess.run(
        ["pgrep", "-f", app_name],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def open_app(app_name: str = APP_NAME, wait: float = 5.0) -> None:
    """Open or focus the MacroFactor app.

    Uses macOS `open -a` which works for both native and "Designed for iPhone" apps.
    """
    logger.info("Opening %s...", app_name)
    subprocess.run(["open", "-a", app_name], check=True)
    time.sleep(wait)
    logger.info("%s is open.", app_name)


def close_app(app_name: str = APP_NAME) -> None:
    """Quit the app gracefully via AppleScript."""
    logger.info("Closing %s...", app_name)
    subprocess.run(
        ["osascript", "-e", f'tell application "{app_name}" to quit'],
        capture_output=True,
    )
    time.sleep(1.0)


def focus_app(app_name: str = APP_NAME) -> None:
    """Bring the app to the foreground via AppleScript."""
    subprocess.run(
        ["osascript", "-e", f'tell application "{app_name}" to activate'],
        capture_output=True,
    )
    time.sleep(0.5)

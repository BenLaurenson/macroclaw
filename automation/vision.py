"""Screen vision utilities — screenshot capture and template matching via OpenCV.

Replaces SikuliX's image recognition with pure Python:
  - pyautogui for screenshots and mouse/keyboard control
  - opencv-python-headless for template matching
"""

import logging
import time
from pathlib import Path

import cv2
import numpy as np
import pyautogui

logger = logging.getLogger("macroclaw.vision")

# Disable pyautogui's built-in pause (we handle timing ourselves)
pyautogui.PAUSE = 0.1
# Fail-safe: move mouse to corner to abort
pyautogui.FAILSAFE = True


IMAGE_DIR = Path(__file__).parent.parent / "images"


def screenshot_to_cv2() -> np.ndarray:
    """Take a screenshot and return it as an OpenCV BGR image."""
    img = pyautogui.screenshot()
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def load_template(name: str, image_dir: Path | None = None) -> np.ndarray:
    """Load a reference image template from disk.

    Args:
        name: Filename (e.g. "more_tab.png") or stem without extension.
        image_dir: Override directory. Defaults to project images/ folder.
    """
    d = image_dir or IMAGE_DIR
    path = d / name
    if not path.suffix:
        path = path.with_suffix(".png")
    if not path.exists():
        raise FileNotFoundError(f"Reference image not found: {path}")
    tmpl = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if tmpl is None:
        raise ValueError(f"Could not read image: {path}")
    return tmpl


def find_on_screen(
    template_name: str,
    confidence: float = 0.80,
    image_dir: Path | None = None,
) -> tuple[int, int] | None:
    """Find a template image on screen using OpenCV template matching.

    Returns:
        (x, y) center coordinates if found above confidence threshold, else None.
    """
    screen = screenshot_to_cv2()
    tmpl = load_template(template_name, image_dir)
    result = cv2.matchTemplate(screen, tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= confidence:
        h, w = tmpl.shape[:2]
        cx = max_loc[0] + w // 2
        cy = max_loc[1] + h // 2
        logger.debug("Found '%s' at (%d, %d) confidence=%.3f", template_name, cx, cy, max_val)
        return (cx, cy)

    logger.debug("'%s' not found (best=%.3f, threshold=%.3f)", template_name, max_val, confidence)
    return None


def wait_and_find(
    template_name: str,
    timeout: float = 10.0,
    interval: float = 0.5,
    confidence: float = 0.80,
    image_dir: Path | None = None,
) -> tuple[int, int]:
    """Wait for a template to appear on screen.

    Returns:
        (x, y) center coordinates.

    Raises:
        TimeoutError if not found within timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        pos = find_on_screen(template_name, confidence, image_dir)
        if pos:
            return pos
        time.sleep(interval)
    raise TimeoutError(f"'{template_name}' not found on screen within {timeout}s")


def click_image(
    template_name: str,
    timeout: float = 10.0,
    confidence: float = 0.80,
    post_delay: float = 1.0,
    image_dir: Path | None = None,
) -> tuple[int, int]:
    """Wait for an image to appear, then click its center.

    Returns:
        (x, y) where the click happened.
    """
    x, y = wait_and_find(template_name, timeout, confidence=confidence, image_dir=image_dir)
    logger.info("Clicking '%s' at (%d, %d)", template_name, x, y)
    pyautogui.click(x, y)
    time.sleep(post_delay)
    return (x, y)


def is_visible(
    template_name: str,
    confidence: float = 0.80,
    image_dir: Path | None = None,
) -> bool:
    """Check if a template is currently visible on screen (no waiting)."""
    return find_on_screen(template_name, confidence, image_dir) is not None


def save_debug_screenshot(label: str = "debug") -> Path:
    """Save a full screenshot for debugging. Returns the path."""
    debug_dir = Path(__file__).parent.parent / "logs" / "screenshots"
    debug_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = debug_dir / f"{ts}_{label}.png"
    pyautogui.screenshot(str(path))
    logger.info("Debug screenshot saved: %s", path)
    return path

"""Export automation — navigates MacroFactor and triggers data exports.

Pure Python replacement for the SikuliX scripts. Uses pyautogui + OpenCV
for visual automation of the MacroFactor "Designed for iPhone" app on macOS.
"""

import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

from automation.app import close_app, focus_app, open_app
from automation.vision import (
    click_image,
    is_visible,
    save_debug_screenshot,
)

logger = logging.getLogger("macroclaw.export")

DOWNLOADS_DIR = Path.home() / "Downloads"
DEFAULT_IMPORTS_DIR = Path(__file__).parent.parent / "data" / "imports"


def _wait_for_download(
    timeout: float = 30.0,
    prefix: str = "MacroFactor",
    extension: str = ".xlsx",
) -> Path:
    """Poll ~/Downloads for a fresh .xlsx file from MacroFactor.

    Returns:
        Path to the downloaded file.

    Raises:
        TimeoutError if no matching file appears.
    """
    logger.info("Waiting for download (timeout: %.0fs)...", timeout)
    deadline = time.time() + timeout

    while time.time() < deadline:
        for f in DOWNLOADS_DIR.iterdir():
            if not f.is_file():
                continue
            if not f.name.lower().endswith(extension.lower()):
                continue
            if prefix.lower() not in f.name.lower():
                continue
            # Only pick up files modified in the last 60 seconds
            age = time.time() - f.stat().st_mtime
            if age < 60:
                logger.info("Download detected: %s (age: %.1fs)", f.name, age)
                time.sleep(1.0)  # Let OS finish writing
                return f
        time.sleep(1.0)

    raise TimeoutError(f"No new '{prefix}*{extension}' in {DOWNLOADS_DIR} within {timeout}s")


def _move_to_imports(source: Path, imports_dir: Path | None = None) -> Path:
    """Move a downloaded file to the imports directory with a timestamp prefix."""
    dest_dir = imports_dir or DEFAULT_IMPORTS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    dest = dest_dir / f"{ts}_{source.name}"
    shutil.move(str(source), str(dest))
    logger.info("Moved to: %s", dest)
    return dest


def _navigate_to_export_screen(confidence: float = 0.80) -> None:
    """Navigate: More tab -> Data Management -> Data Export."""
    click_image("more_tab.png", confidence=confidence)
    click_image("data_management.png", confidence=confidence)
    click_image("data_export.png", confidence=confidence)
    logger.info("Reached Data Export screen.")


def run_daily_export(
    confidence: float = 0.80,
    download_timeout: float = 30.0,
    imports_dir: Path | None = None,
) -> Path:
    """Run the Quick Export flow: last 7 days, nutrition + workouts.

    Returns:
        Path to the imported .xlsx file.
    """
    start = time.time()
    logger.info("=" * 50)
    logger.info("DAILY EXPORT — starting")
    logger.info("=" * 50)

    try:
        open_app()
        focus_app()
        _navigate_to_export_screen(confidence)

        # Quick Export
        click_image("quick_export.png", confidence=confidence)

        # Select Last 7 Days
        click_image("last_7_days.png", confidence=confidence)

        # Verify checkboxes are visible (don't toggle if already on)
        if is_visible("nutrition_checkbox.png", confidence):
            logger.info("Nutrition checkbox visible.")
        if is_visible("workouts_checkbox.png", confidence):
            logger.info("Workouts checkbox visible.")

        # Export
        click_image("export_button.png", confidence=confidence)

        # Handle optional confirmation
        time.sleep(1.0)
        if is_visible("confirm_export.png", confidence):
            click_image("confirm_export.png", confidence=confidence)

        # Wait for download
        downloaded = _wait_for_download(timeout=download_timeout)
        imported = _move_to_imports(downloaded, imports_dir)

        elapsed = time.time() - start
        logger.info("DAILY EXPORT — done in %.1fs -> %s", elapsed, imported)
        return imported

    except Exception:
        save_debug_screenshot("daily_export_error")
        logger.error("DAILY EXPORT — FAILED after %.1fs", time.time() - start)
        raise


def run_bulk_export(
    confidence: float = 0.80,
    download_timeout: float = 120.0,
    imports_dir: Path | None = None,
) -> Path:
    """Run the Granular Export flow: all data, all time.

    Returns:
        Path to the imported .xlsx file.
    """
    start = time.time()
    logger.info("=" * 50)
    logger.info("BULK EXPORT — starting")
    logger.info("=" * 50)

    try:
        open_app()
        focus_app()
        _navigate_to_export_screen(confidence)

        # Granular Export
        click_image("granular_export.png", confidence=confidence)

        # Select all data types
        for checkbox in [
            "nutrition_checkbox.png",
            "workouts_checkbox.png",
            "exercises_checkbox.png",
            "weight_checkbox.png",
        ]:
            if is_visible(checkbox, confidence):
                click_image(checkbox, confidence=confidence, post_delay=0.5)

        # All Time
        click_image("all_time.png", confidence=confidence)

        # Export
        click_image("export_button.png", confidence=confidence)

        # Handle optional confirmation
        time.sleep(1.0)
        if is_visible("confirm_export.png", confidence):
            click_image("confirm_export.png", confidence=confidence)

        # Wait for download (bulk takes longer)
        downloaded = _wait_for_download(timeout=download_timeout)
        imported = _move_to_imports(downloaded, imports_dir)

        elapsed = time.time() - start
        logger.info("BULK EXPORT — done in %.1fs -> %s", elapsed, imported)
        return imported

    except Exception:
        save_debug_screenshot("bulk_export_error")
        logger.error("BULK EXPORT — FAILED after %.1fs", time.time() - start)
        raise

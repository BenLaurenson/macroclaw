"""Export automation — replays recorded click sequences and handles downloads."""

import logging
import shutil
import time
from datetime import datetime
from pathlib import Path

from automation.recorder import replay_sequence

logger = logging.getLogger("macroclaw.export")

DOWNLOADS_DIR = Path.home() / "Downloads"
DEFAULT_IMPORTS_DIR = Path(__file__).parent.parent / "data" / "imports"


def _wait_for_download(
    timeout: float = 30.0,
    prefix: str = "MacroFactor",
    extension: str = ".xlsx",
) -> Path:
    """Poll ~/Downloads for a fresh .xlsx file from MacroFactor."""
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
            age = time.time() - f.stat().st_mtime
            if age < 60:
                logger.info("Download detected: %s (age: %.1fs)", f.name, age)
                time.sleep(1.0)
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


def run_recorded_export(
    name: str,
    speed: float = 1.0,
    download_timeout: float = 30.0,
    imports_dir: Path | None = None,
) -> Path:
    """Replay a recorded sequence, wait for the download, and move to imports.

    Args:
        name: Sequence name ("daily" or "bulk").
        speed: Replay speed multiplier.
        download_timeout: Seconds to wait for the .xlsx file.
        imports_dir: Override imports directory.

    Returns:
        Path to the imported .xlsx file.
    """
    start = time.time()
    logger.info("=" * 50)
    logger.info("%s EXPORT — starting (replay mode)", name.upper())
    logger.info("=" * 50)

    try:
        replay_sequence(name, speed=speed)
        downloaded = _wait_for_download(timeout=download_timeout)
        imported = _move_to_imports(downloaded, imports_dir)
        logger.info("%s EXPORT — done in %.1fs -> %s", name.upper(), time.time() - start, imported)
        return imported
    except Exception:
        logger.error("%s EXPORT — FAILED after %.1fs", name.upper(), time.time() - start)
        raise

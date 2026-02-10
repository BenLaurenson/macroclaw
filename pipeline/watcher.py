"""File system watcher for automatic ingestion of MacroFactor exports.

Monitors a configurable imports directory for new .xlsx files and triggers
the ingestion pipeline when they appear.  Can run as a long-lived daemon
or perform a one-shot scan.
"""

import logging
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent
from watchdog.observers import Observer

from pipeline.ingest import ingest_xlsx

logger = logging.getLogger(__name__)


class _XlsxHandler(FileSystemEventHandler):
    """Watchdog handler that triggers ingestion on new .xlsx files."""

    def __init__(self, db_path: str, archive_dir: str | None = None) -> None:
        super().__init__()
        self.db_path = db_path
        self.archive_dir = archive_dir

    def _process(self, path: str) -> None:
        """Attempt to ingest a file if it is an .xlsx."""
        if not path.lower().endswith(".xlsx"):
            return
        # macOS and some editors write temporary files; ignore those.
        if Path(path).name.startswith(("~$", ".")):
            logger.debug("Ignoring temporary file: %s", path)
            return

        logger.info("Detected new file: %s", path)
        try:
            stats = ingest_xlsx(
                db_path=self.db_path,
                xlsx_path=path,
                archive_dir=self.archive_dir,
            )
            if stats["skipped"]:
                logger.info("Skipped (duplicate): %s", path)
            else:
                logger.info(
                    "Imported %d rows (%s) from %s",
                    stats["rows_imported"],
                    stats["export_type"],
                    path,
                )
        except Exception:
            logger.exception("Failed to ingest %s", path)

    def on_created(self, event: FileCreatedEvent) -> None:  # type: ignore[override]
        if not event.is_directory:
            # Brief pause to let the file finish writing
            time.sleep(0.5)
            self._process(event.src_path)

    def on_moved(self, event: FileMovedEvent) -> None:  # type: ignore[override]
        if not event.is_directory:
            time.sleep(0.5)
            self._process(event.dest_path)


def _scan_existing(
    imports_dir: str, db_path: str, archive_dir: str | None
) -> int:
    """One-shot scan: ingest any .xlsx files already in the imports directory.

    Returns:
        Number of files processed (including skipped duplicates).
    """
    imports_path = Path(imports_dir).expanduser().resolve()
    count = 0
    for xlsx in sorted(imports_path.glob("*.xlsx")):
        if xlsx.name.startswith(("~$", ".")):
            continue
        logger.info("Found existing file: %s", xlsx)
        try:
            ingest_xlsx(
                db_path=db_path,
                xlsx_path=str(xlsx),
                archive_dir=archive_dir,
            )
            count += 1
        except Exception:
            logger.exception("Failed to ingest %s", xlsx)
    return count


def watch(
    db_path: str,
    imports_dir: str,
    archive_dir: str | None = None,
    one_shot: bool = False,
    poll_interval: float = 2.0,
) -> None:
    """Monitor *imports_dir* for new .xlsx files and ingest them.

    Args:
        db_path: Path to the DuckDB database file.
        imports_dir: Directory to watch for incoming exports.
        archive_dir: Directory to move processed files into.
        one_shot: If ``True``, process existing files and return immediately
                  without starting a long-running observer.
        poll_interval: Seconds between observer polls (daemon mode only).
    """
    imports_dir = str(Path(imports_dir).expanduser().resolve())
    Path(imports_dir).mkdir(parents=True, exist_ok=True)

    # Always process files that are already waiting
    processed = _scan_existing(imports_dir, db_path, archive_dir)
    logger.info("One-shot scan complete: processed %d file(s)", processed)

    if one_shot:
        return

    # Start long-running watcher
    handler = _XlsxHandler(db_path=db_path, archive_dir=archive_dir)
    observer = Observer()
    observer.schedule(handler, imports_dir, recursive=False)
    observer.start()
    logger.info("Watching %s for new .xlsx files (Ctrl+C to stop)", imports_dir)

    try:
        while True:
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        logger.info("Stopping file watcher")
    finally:
        observer.stop()
        observer.join()
        logger.info("File watcher stopped")

"""
daily_export.py -- SikuliX Jython script for automated daily MacroFactor export.

This script automates the "Quick Export" flow in the MacroFactor iOS app
running as "Designed for iPhone" on an Apple Silicon Mac.  It is intended
to be executed by SikuliX on a schedule (e.g. via launchd) once per day.

Export parameters:
  - Time range : Last 7 Days (provides overlapping coverage so the
                 downstream pipeline can deduplicate without data gaps)
  - Data types : Nutrition + Workouts
  - Format     : .xlsx (MacroFactor's default export format)

Workflow:
  1. Open / focus the MacroFactor app.
  2. Navigate: More tab -> Data Management -> Data Export -> Quick Export.
  3. Select "Last 7 Days" time range.
  4. Ensure Nutrition and Workouts checkboxes are selected.
  5. Tap the Export button.
  6. Wait for the .xlsx to appear in ~/Downloads.
  7. Move the file to macroclaw/data/imports/ with a timestamped name.
  8. Optionally close the app.

BEFORE RUNNING:
  - Capture all required reference screenshots (see sikuli/images/CAPTURE_GUIDE.md).
  - Verify config/sikuli_config.yaml has correct paths and thresholds.
  - Grant Accessibility and Screen Recording permissions to Java/SikuliX
    in System Settings -> Privacy & Security.

Usage (from terminal):
  java -jar sikulixide-2.0.6.jar -r /path/to/macroclaw/sikuli/scripts/daily_export.py

Or via SikuliX IDE: open this file and press Run.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import os
import sys
import time

# Ensure the scripts directory is on the path so we can import common.py.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from common import (
    load_config,
    setup_logging,
    open_macrofactor,
    close_macrofactor,
    navigate_to_export_screen,
    safe_click,
    safe_exists,
    wait_for_download,
    move_to_imports,
    capture_debug_screenshot,
    format_elapsed,
)

# SikuliX runtime imports.
try:
    from sikuli import FindFailed, sleep
except ImportError:
    pass


# ===========================================================================
# MAIN EXPORT FUNCTION
# ===========================================================================

def run_daily_export(config_path=None):
    """
    Execute the full daily Quick Export workflow.

    Args:
        config_path: Optional path to sikuli_config.yaml.  If None, the
                     default location (config/sikuli_config.yaml) is used.

    Returns:
        Absolute path to the imported .xlsx file on success.

    Raises:
        RuntimeError or FindFailed on unrecoverable failures.
    """
    # ------------------------------------------------------------------
    # 0. Setup
    # ------------------------------------------------------------------
    config = load_config(config_path)
    logger = setup_logging(config.get("log_file"))
    start_time = time.time()

    logger.info("=" * 60)
    logger.info("DAILY EXPORT -- starting")
    logger.info("=" * 60)
    logger.info("Config loaded. Similarity=%.2f", config["similarity"])

    imported_path = None

    try:
        # --------------------------------------------------------------
        # 1. Open the MacroFactor app
        # --------------------------------------------------------------
        open_macrofactor(config, logger)

        # --------------------------------------------------------------
        # 2. Navigate to the Data Export screen
        #    More tab -> Data Management -> Data Export
        # --------------------------------------------------------------
        navigate_to_export_screen(config, logger)

        # --------------------------------------------------------------
        # 3. Select "Quick Export"
        #
        # SCREENSHOT NEEDED: quick_export.png
        #   Capture the "Quick Export" button/row on the Data Export screen.
        # --------------------------------------------------------------
        logger.info("--- Selecting Quick Export ---")
        safe_click("quick_export", config, logger, "Quick Export")
        sleep(config["wait_times"]["between_actions"])

        # --------------------------------------------------------------
        # 4. Select "Last 7 Days" time range
        #
        # SCREENSHOT NEEDED: last_7_days.png
        #   Capture the "Last 7 Days" option.  It may be a segmented
        #   control, a dropdown, or a list row depending on app version.
        #
        # We select 7 days intentionally even though we run daily.
        # The overlap is harmless -- the downstream DuckDB pipeline
        # deduplicates by date -- and it provides resilience against
        # missed runs.
        # --------------------------------------------------------------
        logger.info("--- Selecting time range: Last 7 Days ---")
        safe_click("last_7_days", config, logger, "Last 7 Days")
        sleep(config["wait_times"]["between_actions"])

        # --------------------------------------------------------------
        # 5. Ensure data types are selected: Nutrition + Workouts
        #
        # SCREENSHOTS NEEDED:
        #   nutrition_checkbox.png  -- the Nutrition toggle/checkbox
        #   workouts_checkbox.png   -- the Workouts toggle/checkbox
        #
        # Strategy: check if each checkbox is already selected.  If we
        # cannot distinguish selected vs. unselected states with a
        # single image, we simply click each one.  If the app uses
        # toggles, clicking an already-on toggle turns it off, so we
        # need TWO images per toggle (on and off states) or careful
        # threshold tuning.
        #
        # TEMPLATE NOTE: The simplest approach for Quick Export is that
        # both are selected by default.  If your app version does NOT
        # pre-select them, uncomment the click lines below.
        # --------------------------------------------------------------
        logger.info("--- Verifying data type selections ---")

        # Option A: Click only if not already selected (requires separate
        # "unchecked" images -- nutrition_unchecked.png, etc.)
        #
        # if safe_exists("nutrition_unchecked", config, logger, timeout=2):
        #     safe_click("nutrition_unchecked", config, logger, "Nutrition (enable)")
        #
        # if safe_exists("workouts_unchecked", config, logger, timeout=2):
        #     safe_click("workouts_unchecked", config, logger, "Workouts (enable)")

        # Option B: Assume defaults are correct; just verify they are visible.
        if safe_exists("nutrition_checkbox", config, logger, timeout=3):
            logger.info("Nutrition checkbox is visible.")
        else:
            logger.warning("Nutrition checkbox NOT found -- it may be off-screen or "
                           "already selected in a collapsed view.")

        if safe_exists("workouts_checkbox", config, logger, timeout=3):
            logger.info("Workouts checkbox is visible.")
        else:
            logger.warning("Workouts checkbox NOT found -- see note above.")

        # --------------------------------------------------------------
        # 6. Trigger the export
        #
        # SCREENSHOT NEEDED: export_button.png
        #   Capture the primary "Export" / "Export Data" button.
        #
        # Some app versions show a confirmation dialog after tapping
        # Export.  If yours does, also capture confirm_export.png and
        # uncomment the confirmation click below.
        # --------------------------------------------------------------
        logger.info("--- Triggering export ---")
        safe_click("export_button", config, logger, "Export button")
        sleep(config["wait_times"]["between_actions"])

        # Handle optional confirmation dialog.
        if safe_exists("confirm_export", config, logger, timeout=3):
            logger.info("Confirmation dialog detected; confirming.")
            safe_click("confirm_export", config, logger, "Confirm export")
            sleep(config["wait_times"]["between_actions"])

        # --------------------------------------------------------------
        # 7. Wait for the .xlsx to appear in Downloads
        # --------------------------------------------------------------
        logger.info("--- Waiting for download ---")
        downloaded_path = wait_for_download(config, logger)
        logger.info("Export downloaded: %s", downloaded_path)

        # --------------------------------------------------------------
        # 8. Move the file to the imports directory
        # --------------------------------------------------------------
        logger.info("--- Moving file to imports ---")
        imported_path = move_to_imports(downloaded_path, config, logger)
        logger.info("File imported: %s", imported_path)

        # --------------------------------------------------------------
        # 9. (Optional) Close the app to free resources
        # --------------------------------------------------------------
        # Uncomment the next line if you want the app closed after export:
        # close_macrofactor(config, logger)

        logger.info("=" * 60)
        logger.info("DAILY EXPORT -- completed successfully in %s",
                     format_elapsed(start_time))
        logger.info("  Imported file: %s", imported_path)
        logger.info("=" * 60)

    except FindFailed as exc:
        # A UI element was not found within the timeout.
        logger.error("UI element not found: %s", exc)
        capture_debug_screenshot(config, logger, label="daily_export_FindFailed")
        logger.error("DAILY EXPORT -- FAILED after %s", format_elapsed(start_time))
        raise

    except TimeoutError as exc:
        # The download did not appear in time.
        logger.error("Download timeout: %s", exc)
        capture_debug_screenshot(config, logger, label="daily_export_DownloadTimeout")
        logger.error("DAILY EXPORT -- FAILED after %s", format_elapsed(start_time))
        raise

    except Exception as exc:
        # Catch-all for unexpected errors.
        logger.error("Unexpected error: %s: %s", type(exc).__name__, exc)
        capture_debug_screenshot(config, logger, label="daily_export_error")
        logger.error("DAILY EXPORT -- FAILED after %s", format_elapsed(start_time))
        raise

    return imported_path


# ===========================================================================
# ENTRY POINT
# ===========================================================================

if __name__ == "__main__":
    # When executed directly by SikuliX or via command line.
    #
    # Optional: pass a custom config path as the first argument.
    #   java -jar sikulixide.jar -r daily_export.py -- /path/to/config.yaml
    #
    # SikuliX passes script arguments after "--" in sys.argv.
    custom_config = None
    if len(sys.argv) > 1:
        candidate = sys.argv[-1]
        if candidate.endswith(".yaml") or candidate.endswith(".yml"):
            custom_config = candidate

    result = run_daily_export(config_path=custom_config)
    if result:
        print("Export complete: %s" % result)
    else:
        print("Export produced no file.")
        sys.exit(1)

"""
bulk_export.py -- SikuliX Jython script for bulk/historical MacroFactor export.

This script automates the "Granular Export" flow in the MacroFactor iOS app
running as "Designed for iPhone" on an Apple Silicon Mac.  It exports ALL
available data types over the entire account history.

This is designed to be run:
  - Once during initial setup to bootstrap the data warehouse.
  - Periodically (weekly or monthly) as a comprehensive backup/sync.

Export parameters:
  - Time range  : All Time
  - Data types  : Nutrition, Workouts, Exercises, Weight (all available)
  - Format      : .xlsx (MacroFactor's default export format)

Workflow:
  1. Open / focus the MacroFactor app.
  2. Navigate: More tab -> Data Management -> Data Export -> Granular Export.
  3. Select ALL data-type checkboxes.
  4. Select "All Time" time range.
  5. Tap the Export button.
  6. Wait for the .xlsx to appear in ~/Downloads.
  7. Move the file to macroclaw/data/imports/ with a timestamped name.
  8. Optionally close the app.

BEFORE RUNNING:
  - Capture all required reference screenshots (see sikuli/images/CAPTURE_GUIDE.md).
  - Verify config/sikuli_config.yaml has correct paths and thresholds.
  - Grant Accessibility and Screen Recording permissions to Java/SikuliX
    in System Settings -> Privacy & Security.
  - NOTE: A full "All Time" export may take significantly longer to generate
    than a 7-day Quick Export.  Consider increasing download_timeout in your
    config (60-120 seconds is a reasonable starting point for large accounts).

Usage (from terminal):
  java -jar sikulixide-2.0.6.jar -r /path/to/macroclaw/sikuli/scripts/bulk_export.py

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
# DATA TYPE SELECTION
# ===========================================================================

# All data types available in the Granular Export screen.
# Each entry is a tuple: (image_key, human_label).
# The image_key maps to an entry in common.IMAGES.
ALL_DATA_TYPES = [
    ("nutrition_checkbox",  "Nutrition"),
    ("workouts_checkbox",   "Workouts"),
    ("exercises_checkbox",  "Exercises"),
    ("weight_checkbox",     "Weight"),
]


def select_all_data_types(config, logger):
    """
    Ensure every data-type checkbox on the Granular Export screen is selected.

    Strategy:
      For each data type, check if the checkbox is visible.  If visible,
      click it to toggle it on.

    IMPORTANT TEMPLATE NOTE:
      If your MacroFactor version uses toggles (not checkboxes), clicking an
      already-on toggle will turn it OFF.  In that case you need two images
      per toggle -- one for the "on" state and one for the "off" state --
      and only click when the "off" image is found.  Adjust the logic below
      to match your app's behavior:

        if safe_exists("nutrition_off", config, logger, timeout=2):
            safe_click("nutrition_off", config, logger, "Nutrition (enable)")
        else:
            logger.info("Nutrition already enabled.")

      For the default template, we assume that checkboxes start UNCHECKED
      and we click each one to enable it.  If your export screen pre-selects
      all types, you can skip this step entirely.
    """
    logger.info("--- Selecting all data types ---")

    for image_key, label in ALL_DATA_TYPES:
        try:
            if safe_exists(image_key, config, logger, timeout=3):
                logger.info("Found '%s' checkbox; clicking to ensure selection.", label)
                safe_click(image_key, config, logger, label)
                sleep(config["wait_times"]["post_click"])
            else:
                # The checkbox image was not found.  This could mean:
                # - The type is already selected and looks different.
                # - The type is not available in this app version.
                # - The element is off-screen (may need scrolling).
                logger.warning(
                    "'%s' checkbox not found on screen. It may already be "
                    "selected, unavailable, or require scrolling.", label
                )
        except Exception as exc:
            logger.warning("Error selecting '%s': %s", label, exc)
            # Continue with remaining types rather than aborting.

    logger.info("Data type selection complete.")


# ===========================================================================
# SCROLLING HELPER
# ===========================================================================

def scroll_down_in_app(config, logger, amount=3):
    """
    Scroll down within the MacroFactor app window.

    Useful if data-type checkboxes or the time-range picker are below
    the visible fold in the Granular Export screen.

    Args:
        config: Config dict.
        logger: Logger instance.
        amount: Number of scroll "clicks" (platform-dependent).

    TEMPLATE NOTE:
      SikuliX scroll behavior varies by platform.  On macOS, wheel(direction, steps)
      or type(Key.DOWN) may work.  Adjust to match your setup.
    """
    try:
        from sikuli import wheel, WHEEL_DOWN
        logger.info("Scrolling down %d steps.", amount)
        wheel(WHEEL_DOWN, amount)
        sleep(config["wait_times"]["post_click"])
    except ImportError:
        logger.warning("Scroll functions not available in this SikuliX version.")
    except Exception as exc:
        logger.warning("Scroll failed: %s", exc)


# ===========================================================================
# MAIN EXPORT FUNCTION
# ===========================================================================

def run_bulk_export(config_path=None):
    """
    Execute the full Granular Export workflow for all data, all time.

    Args:
        config_path: Optional path to sikuli_config.yaml.

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
    logger.info("BULK EXPORT -- starting")
    logger.info("=" * 60)
    logger.info("Config loaded. Similarity=%.2f", config["similarity"])

    # For bulk exports, increase the download timeout if not already high.
    # A full All Time export can take a while to generate server-side.
    if config["wait_times"]["download_timeout"] < 60:
        logger.info("Increasing download_timeout to 120s for bulk export.")
        config["wait_times"]["download_timeout"] = 120

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
        # 3. Select "Granular Export"
        #
        # SCREENSHOT NEEDED: granular_export.png
        #   Capture the "Granular Export" button/row on the Data Export
        #   screen.  This is typically below "Quick Export" on the same
        #   screen.
        # --------------------------------------------------------------
        logger.info("--- Selecting Granular Export ---")
        safe_click("granular_export", config, logger, "Granular Export")
        sleep(config["wait_times"]["between_actions"])

        # --------------------------------------------------------------
        # 4. Select ALL data types
        #
        # SCREENSHOTS NEEDED (one for each data type):
        #   nutrition_checkbox.png
        #   workouts_checkbox.png
        #   exercises_checkbox.png
        #   weight_checkbox.png
        #
        # The Granular Export screen lists all exportable data categories
        # with checkboxes or toggles.  We want everything selected.
        # --------------------------------------------------------------
        select_all_data_types(config, logger)

        # If some checkboxes were below the fold, scroll and try again.
        # Uncomment the following block if your screen requires scrolling:
        #
        # scroll_down_in_app(config, logger, amount=3)
        # select_all_data_types(config, logger)

        # --------------------------------------------------------------
        # 5. Select "All Time" time range
        #
        # SCREENSHOT NEEDED: all_time.png
        #   Capture the "All Time" option in the time-range selector.
        #   This may be a segmented control, a picker, or a list row.
        #
        # NOTE: If "All Time" is not visible, you may need to scroll
        # down or tap a "Time Range" dropdown first.
        # --------------------------------------------------------------
        logger.info("--- Selecting time range: All Time ---")
        safe_click("all_time", config, logger, "All Time")
        sleep(config["wait_times"]["between_actions"])

        # --------------------------------------------------------------
        # 6. Trigger the export
        #
        # SCREENSHOT NEEDED: export_button.png
        #   Capture the primary "Export" / "Export Data" action button.
        #   This is the same image used by daily_export.py.
        #
        # Bulk exports may take longer to prepare.  MacroFactor might
        # show a progress indicator or spinner.
        # --------------------------------------------------------------
        logger.info("--- Triggering export ---")
        safe_click("export_button", config, logger, "Export button")
        sleep(config["wait_times"]["between_actions"])

        # Handle optional confirmation dialog.
        if safe_exists("confirm_export", config, logger, timeout=5):
            logger.info("Confirmation dialog detected; confirming.")
            safe_click("confirm_export", config, logger, "Confirm export")
            sleep(config["wait_times"]["between_actions"])

        # --------------------------------------------------------------
        # 7. Wait for the .xlsx to appear in Downloads
        #
        # Bulk exports can take significantly longer.  The timeout was
        # increased at the top of this function.
        # --------------------------------------------------------------
        logger.info("--- Waiting for download (bulk -- may take a while) ---")
        downloaded_path = wait_for_download(config, logger)
        logger.info("Export downloaded: %s", downloaded_path)

        # --------------------------------------------------------------
        # 8. Move the file to the imports directory
        # --------------------------------------------------------------
        logger.info("--- Moving file to imports ---")
        imported_path = move_to_imports(downloaded_path, config, logger)
        logger.info("File imported: %s", imported_path)

        # --------------------------------------------------------------
        # 9. (Optional) Close the app
        # --------------------------------------------------------------
        # Uncomment if you want the app closed after export:
        # close_macrofactor(config, logger)

        logger.info("=" * 60)
        logger.info("BULK EXPORT -- completed successfully in %s",
                     format_elapsed(start_time))
        logger.info("  Imported file: %s", imported_path)
        logger.info("=" * 60)

    except FindFailed as exc:
        # A required UI element was not found.
        logger.error("UI element not found: %s", exc)
        capture_debug_screenshot(config, logger, label="bulk_export_FindFailed")
        logger.error("BULK EXPORT -- FAILED after %s", format_elapsed(start_time))
        raise

    except TimeoutError as exc:
        # The download did not appear in time.
        logger.error("Download timeout: %s", exc)
        logger.error(
            "TIP: Bulk exports with large datasets may need a longer timeout. "
            "Increase 'download_timeout' in your config (try 120-300 seconds)."
        )
        capture_debug_screenshot(config, logger, label="bulk_export_DownloadTimeout")
        logger.error("BULK EXPORT -- FAILED after %s", format_elapsed(start_time))
        raise

    except Exception as exc:
        # Catch-all for unexpected errors.
        logger.error("Unexpected error: %s: %s", type(exc).__name__, exc)
        capture_debug_screenshot(config, logger, label="bulk_export_error")
        logger.error("BULK EXPORT -- FAILED after %s", format_elapsed(start_time))
        raise

    return imported_path


# ===========================================================================
# ENTRY POINT
# ===========================================================================

if __name__ == "__main__":
    # When executed directly by SikuliX or via command line.
    #
    # Optional: pass a custom config path as the first argument.
    #   java -jar sikulixide.jar -r bulk_export.py -- /path/to/config.yaml
    custom_config = None
    if len(sys.argv) > 1:
        candidate = sys.argv[-1]
        if candidate.endswith(".yaml") or candidate.endswith(".yml"):
            custom_config = candidate

    result = run_bulk_export(config_path=custom_config)
    if result:
        print("Bulk export complete: %s" % result)
    else:
        print("Bulk export produced no file.")
        sys.exit(1)

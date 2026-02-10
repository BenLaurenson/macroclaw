"""
common.py -- Shared utilities for MacroClaw SikuliX automation scripts.

This module provides configuration loading, logging, navigation helpers,
screenshot capture for debugging, and file-move utilities used by both
the daily_export.py and bulk_export.py scripts.

SikuliX runs on Jython 2.7, so this code must be compatible with
Python 2.7 syntax and the Java-based SikuliX API.

IMPORTANT: SikuliX imports (Region, Pattern, App, etc.) are available
at runtime when executed inside the SikuliX environment. They will NOT
resolve in a standard Python/Jython interpreter outside SikuliX.
"""

# ---------------------------------------------------------------------------
# Standard-library imports (Jython 2.7 compatible)
# ---------------------------------------------------------------------------
import os
import sys
import time
import shutil
import logging
import datetime

# ---------------------------------------------------------------------------
# SikuliX imports -- these are injected by the SikuliX runtime.
# When editing outside SikuliX, your IDE will flag these as missing;
# that is expected.
# ---------------------------------------------------------------------------
try:
    from sikuli import (
        App,
        Pattern,
        Region,
        Screen,
        Key,
        KeyModifier,
        Settings,
        wait,
        click,
        type as sikuli_type,
        exists,
        capture,
        sleep,
        SCREEN,
        FindFailed,
    )
    SIKULI_AVAILABLE = True
except ImportError:
    # Running outside SikuliX (e.g. unit-testing helpers).
    SIKULI_AVAILABLE = False

# ---------------------------------------------------------------------------
# Optional: PyYAML for config loading.
# SikuliX ships Jython, which may or may not have PyYAML installed.
# We fall back to a simple built-in parser if yaml is not available.
# ---------------------------------------------------------------------------
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# ===========================================================================
# CONSTANTS
# ===========================================================================

# Base directories -- derived from this file's location.
# Expected layout:
#   macroclaw/
#     sikuli/
#       scripts/   <-- this file lives here
#       images/    <-- reference screenshots live here
#     data/
#       imports/   <-- where exported .xlsx files are moved to
#     config/
#       sikuli_config.yaml
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SIKULI_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_DIR = os.path.dirname(SIKULI_DIR)

# Image directory -- contains captured reference screenshots.
IMAGE_DIR = os.path.join(SIKULI_DIR, "images")

# Default imports directory -- where exported files are deposited.
DEFAULT_IMPORTS_DIR = os.path.join(PROJECT_DIR, "data", "imports")

# Default config file path.
DEFAULT_CONFIG_PATH = os.path.join(PROJECT_DIR, "config", "sikuli_config.yaml")

# Default log file path.
DEFAULT_LOG_DIR = os.path.join(PROJECT_DIR, "logs")
DEFAULT_LOG_FILE = os.path.join(DEFAULT_LOG_DIR, "sikuli_export.log")

# macOS Downloads folder (used as the default export landing zone).
DOWNLOADS_DIR = os.path.expanduser("~/Downloads")

# ---------------------------------------------------------------------------
# Reference image filenames.  Each corresponds to a .png that the user must
# capture from their own MacroFactor installation.  See images/CAPTURE_GUIDE.md
# for detailed instructions on what to capture for each one.
# ---------------------------------------------------------------------------
IMAGES = {
    # Bottom navigation bar
    "more_tab":              "more_tab.png",
    # "More" menu items
    "data_management":       "data_management.png",
    # Data Management screen
    "data_export":           "data_export.png",
    # Export type selection
    "quick_export":          "quick_export.png",
    "granular_export":       "granular_export.png",
    # Time-range options
    "last_7_days":           "last_7_days.png",
    "all_time":              "all_time.png",
    # Data-type checkboxes / toggles
    "nutrition_checkbox":    "nutrition_checkbox.png",
    "workouts_checkbox":     "workouts_checkbox.png",
    "exercises_checkbox":    "exercises_checkbox.png",
    "weight_checkbox":       "weight_checkbox.png",
    # Action buttons
    "export_button":         "export_button.png",
    "confirm_export":        "confirm_export.png",
    # App icon or window title (for opening / focusing the app)
    "macrofactor_icon":      "macrofactor_icon.png",
    # Optional: back/close buttons for navigation recovery
    "back_button":           "back_button.png",
    "close_button":          "close_button.png",
}

# ---------------------------------------------------------------------------
# Default timing configuration (seconds).  Override via sikuli_config.yaml.
# ---------------------------------------------------------------------------
DEFAULT_WAIT_TIMES = {
    # How long to wait for the app to launch and become ready.
    "app_launch":       8,
    # Standard pause between UI actions (tap/click).
    "between_actions":  1.5,
    # How long to wait for a specific UI element to appear.
    "element_timeout":  10,
    # How long to wait for the .xlsx file to land in Downloads.
    "download_timeout": 30,
    # Short pause after clicking, before the next find.
    "post_click":       1.0,
}

# Default similarity threshold for Pattern matching (0.0 - 1.0).
# Lower values are more forgiving but risk false positives.
# Higher values require a closer match but may fail on slight rendering diffs.
DEFAULT_SIMILARITY = 0.80

# MacroFactor app name as macOS knows it.
# "Designed for iPhone" apps appear with their App Store name.
MACROFACTOR_APP_NAME = "MacroFactor"


# ===========================================================================
# CONFIGURATION LOADER
# ===========================================================================

def load_config(config_path=None):
    """
    Load configuration from a YAML file and merge with defaults.

    If the config file does not exist or PyYAML is unavailable, returns a
    dict populated entirely from built-in defaults so scripts can still run.

    Config file format (sikuli_config.yaml):
    -----------------------------------------
    similarity: 0.82
    wait_times:
      app_launch: 10
      between_actions: 2.0
      element_timeout: 15
      download_timeout: 45
      post_click: 1.2
    imports_dir: /Users/you/projects/macroclaw/data/imports
    downloads_dir: ~/Downloads
    app_name: MacroFactor
    log_file: /Users/you/projects/macroclaw/logs/sikuli_export.log
    -----------------------------------------

    Returns:
        dict with all configuration values.
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    config = {
        "similarity":    DEFAULT_SIMILARITY,
        "wait_times":    dict(DEFAULT_WAIT_TIMES),
        "imports_dir":   DEFAULT_IMPORTS_DIR,
        "downloads_dir": DOWNLOADS_DIR,
        "app_name":      MACROFACTOR_APP_NAME,
        "log_file":      DEFAULT_LOG_FILE,
        "image_dir":     IMAGE_DIR,
    }

    if not os.path.isfile(config_path):
        return config

    if not YAML_AVAILABLE:
        # Without PyYAML we cannot parse the config; use defaults.
        return config

    try:
        with open(config_path, "r") as fh:
            user_cfg = yaml.safe_load(fh) or {}
    except Exception:
        # If the file is malformed, fall back to defaults.
        return config

    # Merge top-level keys.
    for key in ("similarity", "imports_dir", "downloads_dir", "app_name", "log_file", "image_dir"):
        if key in user_cfg:
            val = user_cfg[key]
            # Expand ~ in paths.
            if isinstance(val, str) and "~" in val:
                val = os.path.expanduser(val)
            config[key] = val

    # Merge wait_times dict (only override keys the user provided).
    if "wait_times" in user_cfg and isinstance(user_cfg["wait_times"], dict):
        for wk, wv in user_cfg["wait_times"].items():
            config["wait_times"][wk] = float(wv)

    return config


# ===========================================================================
# LOGGING SETUP
# ===========================================================================

def setup_logging(log_file=None, level=logging.INFO):
    """
    Configure Python logging to write to both a file and stdout.

    Args:
        log_file: Path to the log file.  Parent directories are created
                  automatically if they do not exist.
        level:    Logging level (default INFO).

    Returns:
        A logging.Logger instance named "macroclaw.sikuli".
    """
    if log_file is None:
        log_file = DEFAULT_LOG_FILE

    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.isdir(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger("macroclaw.sikuli")
    logger.setLevel(level)

    # Avoid duplicate handlers on repeated calls.
    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "%(asctime)s  [%(levelname)-7s]  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler.
    fh = logging.FileHandler(log_file)
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console handler.
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


# ===========================================================================
# IMAGE HELPERS
# ===========================================================================

def img(name, config=None):
    """
    Return the full path to a reference screenshot image.

    Args:
        name:   Key from the IMAGES dict (e.g. "more_tab") OR a raw filename.
        config: Config dict (used to resolve image_dir).  If None, uses
                the module-level IMAGE_DIR constant.

    Returns:
        Absolute path string to the .png file.

    Raises:
        FileNotFoundError if the resolved path does not exist on disk.
    """
    image_dir = config["image_dir"] if config else IMAGE_DIR
    filename = IMAGES.get(name, name)
    path = os.path.join(image_dir, filename)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            "Reference image not found: %s\n"
            "  Expected at: %s\n"
            "  Have you captured all required screenshots?  "
            "See sikuli/images/CAPTURE_GUIDE.md" % (name, path)
        )
    return path


def make_pattern(name, config=None):
    """
    Build a SikuliX Pattern for the named image with the configured
    similarity threshold.

    Args:
        name:   Key from the IMAGES dict.
        config: Config dict.

    Returns:
        A SikuliX Pattern object ready to pass to wait()/click()/exists().
    """
    if not SIKULI_AVAILABLE:
        raise RuntimeError("SikuliX runtime is not available.")

    similarity = config["similarity"] if config else DEFAULT_SIMILARITY
    image_path = img(name, config)
    return Pattern(image_path).similar(similarity)


# ===========================================================================
# APP MANAGEMENT
# ===========================================================================

def open_macrofactor(config, logger):
    """
    Launch or bring MacroFactor to the foreground.

    MacroFactor is an iOS app running via "Designed for iPhone" on Apple
    Silicon Macs.  It behaves like a regular macOS app for launch/focus
    purposes but renders in a fixed iPhone-sized window.

    Args:
        config: Config dict.
        logger: Logger instance.

    Returns:
        True if the app window is visible after launch.

    Raises:
        RuntimeError if the app cannot be opened within the timeout.
    """
    if not SIKULI_AVAILABLE:
        raise RuntimeError("SikuliX runtime is not available.")

    app_name = config.get("app_name", MACROFACTOR_APP_NAME)
    launch_wait = config["wait_times"]["app_launch"]

    logger.info("Opening app: %s", app_name)
    app = App(app_name)

    # If already running, just focus it.
    if app.isRunning():
        logger.info("App is already running; bringing to foreground.")
        app.focus()
        sleep(config["wait_times"]["post_click"])
        return True

    # Launch fresh.
    app.open()
    logger.info("Waiting %.1f seconds for app to launch...", launch_wait)
    sleep(launch_wait)

    # Verify the app appeared.
    if not app.isRunning():
        raise RuntimeError(
            "Failed to launch %s within %.0f seconds." % (app_name, launch_wait)
        )

    app.focus()
    sleep(config["wait_times"]["post_click"])
    logger.info("App is open and focused.")
    return True


def close_macrofactor(config, logger):
    """
    Close the MacroFactor app window.

    Args:
        config: Config dict.
        logger: Logger instance.
    """
    if not SIKULI_AVAILABLE:
        return

    app_name = config.get("app_name", MACROFACTOR_APP_NAME)
    app = App(app_name)
    if app.isRunning():
        logger.info("Closing app: %s", app_name)
        app.close()
        sleep(config["wait_times"]["post_click"])
    else:
        logger.info("App %s is not running; nothing to close.", app_name)


# ===========================================================================
# NAVIGATION HELPERS
# ===========================================================================

def safe_click(target_name, config, logger, description=None):
    """
    Wait for a UI element to appear, then click it.

    This is the fundamental interaction primitive.  All navigation is
    built from sequences of safe_click() calls.

    Args:
        target_name: Key from the IMAGES dict.
        config:      Config dict.
        logger:      Logger instance.
        description: Human-readable label for log messages (defaults to
                     target_name).

    Raises:
        FindFailed (SikuliX exception) if the element does not appear
        within the configured timeout.
    """
    if not SIKULI_AVAILABLE:
        raise RuntimeError("SikuliX runtime is not available.")

    desc = description or target_name
    timeout = config["wait_times"]["element_timeout"]
    pattern = make_pattern(target_name, config)

    logger.info("Waiting for '%s' (timeout: %.0fs)...", desc, timeout)
    wait(pattern, timeout)
    logger.info("Found '%s'; clicking.", desc)
    click(pattern)
    sleep(config["wait_times"]["post_click"])


def safe_exists(target_name, config, logger, timeout=None):
    """
    Check whether a UI element is currently visible on screen.

    Does NOT click -- just returns True/False.

    Args:
        target_name: Key from the IMAGES dict.
        config:      Config dict.
        logger:      Logger instance.
        timeout:     Seconds to wait.  Defaults to element_timeout.

    Returns:
        True if found, False otherwise.
    """
    if not SIKULI_AVAILABLE:
        return False

    if timeout is None:
        timeout = config["wait_times"]["element_timeout"]

    pattern = make_pattern(target_name, config)
    result = exists(pattern, timeout)
    return result is not None


def navigate_to_more_tab(config, logger):
    """
    Tap the "More" tab in the MacroFactor bottom navigation bar.

    Precondition: MacroFactor app is open and focused.
    """
    logger.info("--- Navigating to More tab ---")
    safe_click("more_tab", config, logger, "More tab")
    sleep(config["wait_times"]["between_actions"])


def navigate_to_data_management(config, logger):
    """
    From the More screen, tap "Data Management".
    """
    logger.info("--- Navigating to Data Management ---")
    safe_click("data_management", config, logger, "Data Management")
    sleep(config["wait_times"]["between_actions"])


def navigate_to_data_export(config, logger):
    """
    From Data Management, tap "Data Export".
    """
    logger.info("--- Navigating to Data Export ---")
    safe_click("data_export", config, logger, "Data Export")
    sleep(config["wait_times"]["between_actions"])


def navigate_to_export_screen(config, logger):
    """
    Full navigation sequence: More -> Data Management -> Data Export.

    Call this after open_macrofactor() to reach the export screen.
    """
    navigate_to_more_tab(config, logger)
    navigate_to_data_management(config, logger)
    navigate_to_data_export(config, logger)
    logger.info("Reached the Data Export screen.")


# ===========================================================================
# DOWNLOAD HANDLING
# ===========================================================================

def wait_for_download(config, logger, prefix="MacroFactor", extension=".xlsx"):
    """
    Wait for a new .xlsx file to appear in the Downloads directory.

    MacroFactor exports land in ~/Downloads with a name like
    "MacroFactor Export YYYY-MM-DD.xlsx" (the exact format may vary).

    Strategy:
      1. Record existing .xlsx files in Downloads before triggering export.
      2. Poll the directory until a new matching file appears.

    NOTE: Call get_existing_downloads() BEFORE triggering the export,
    then pass the result to this function via the pre_files parameter.
    This two-step approach is handled by the caller scripts.

    Args:
        config:    Config dict.
        logger:    Logger instance.
        prefix:    Filename prefix to look for (case-insensitive).
        extension: File extension to match.

    Returns:
        Absolute path to the newly downloaded file.

    Raises:
        TimeoutError if no new file appears within download_timeout seconds.
    """
    downloads_dir = config.get("downloads_dir", DOWNLOADS_DIR)
    timeout = config["wait_times"]["download_timeout"]
    poll_interval = 1.0  # seconds between checks

    logger.info(
        "Watching for new '%s*%s' in %s (timeout: %.0fs)...",
        prefix, extension, downloads_dir, timeout,
    )

    start = time.time()
    while (time.time() - start) < timeout:
        for fname in os.listdir(downloads_dir):
            fpath = os.path.join(downloads_dir, fname)
            if not os.path.isfile(fpath):
                continue
            if not fname.lower().endswith(extension.lower()):
                continue
            if prefix.lower() not in fname.lower():
                continue
            # Check the file was modified recently (within the last 60 seconds)
            # to ensure it is the fresh export, not an old one.
            mtime = os.path.getmtime(fpath)
            age = time.time() - mtime
            if age < 60:
                logger.info("Download detected: %s (age: %.1fs)", fname, age)
                # Brief pause to let the OS finish writing.
                time.sleep(1.0)
                return fpath
        time.sleep(poll_interval)

    raise TimeoutError(
        "No new '%s*%s' file appeared in %s within %.0f seconds."
        % (prefix, extension, downloads_dir, timeout)
    )


def get_existing_downloads(config, prefix="MacroFactor", extension=".xlsx"):
    """
    Return a set of existing matching filenames in the Downloads directory.

    Call this BEFORE triggering an export so that wait_for_download() can
    identify which file is new.

    Returns:
        set of absolute file paths.
    """
    downloads_dir = config.get("downloads_dir", DOWNLOADS_DIR)
    existing = set()
    for fname in os.listdir(downloads_dir):
        fpath = os.path.join(downloads_dir, fname)
        if not os.path.isfile(fpath):
            continue
        if fname.lower().endswith(extension.lower()) and prefix.lower() in fname.lower():
            existing.add(fpath)
    return existing


def move_to_imports(source_path, config, logger):
    """
    Move a downloaded .xlsx file from Downloads into the macroclaw
    imports directory.

    The file is renamed with an ISO-8601 timestamp prefix to avoid
    collisions and to make chronological ordering obvious:
        2025-06-15T08-30-00_MacroFactor_Export.xlsx

    Args:
        source_path: Absolute path to the file in Downloads.
        config:      Config dict.
        logger:      Logger instance.

    Returns:
        Absolute path to the file in its new location.
    """
    imports_dir = config.get("imports_dir", DEFAULT_IMPORTS_DIR)
    if not os.path.isdir(imports_dir):
        logger.info("Creating imports directory: %s", imports_dir)
        os.makedirs(imports_dir)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    original_name = os.path.basename(source_path)
    new_name = "%s_%s" % (timestamp, original_name)
    dest_path = os.path.join(imports_dir, new_name)

    logger.info("Moving: %s -> %s", source_path, dest_path)
    shutil.move(source_path, dest_path)
    logger.info("File moved successfully.")
    return dest_path


# ===========================================================================
# DEBUGGING HELPERS
# ===========================================================================

def capture_debug_screenshot(config, logger, label="debug"):
    """
    Take a full-screen screenshot and save it for post-mortem debugging.

    Screenshots are saved to PROJECT_DIR/logs/screenshots/ with a
    timestamped filename.

    Args:
        config: Config dict.
        logger: Logger instance.
        label:  Short label included in the filename.

    Returns:
        Path to the saved screenshot, or None if capture failed.
    """
    screenshot_dir = os.path.join(PROJECT_DIR, "logs", "screenshots")
    if not os.path.isdir(screenshot_dir):
        os.makedirs(screenshot_dir)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = "%s_%s.png" % (timestamp, label)
    dest_path = os.path.join(screenshot_dir, filename)

    if not SIKULI_AVAILABLE:
        logger.warning("Cannot capture screenshot: SikuliX runtime not available.")
        return None

    try:
        # SikuliX capture() returns the path to a temp file.
        temp_path = capture(SCREEN)
        if temp_path:
            shutil.copy(temp_path, dest_path)
            logger.info("Debug screenshot saved: %s", dest_path)
            return dest_path
        else:
            logger.warning("capture() returned None.")
            return None
    except Exception as exc:
        logger.warning("Failed to capture debug screenshot: %s", exc)
        return None


def format_elapsed(start_time):
    """
    Return a human-readable string for elapsed time since start_time.

    Args:
        start_time: Value from time.time() at the start of the operation.

    Returns:
        String like "12.3s" or "2m 5.1s".
    """
    elapsed = time.time() - start_time
    if elapsed < 60:
        return "%.1fs" % elapsed
    minutes = int(elapsed // 60)
    seconds = elapsed % 60
    return "%dm %.1fs" % (minutes, seconds)

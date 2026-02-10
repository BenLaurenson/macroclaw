#!/usr/bin/env bash
# daily_export.sh -- Wrapper to run the SikuliX daily export automation.
#
# Called by launchd (com.macroclaw.daily-export) or manually from the terminal.
# Locates the SikuliX JAR and executes daily_export.py as a Jython script.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_FILE="$PROJECT_DIR/config/sikuli_config.yaml"

# --- Defaults (override via config or environment) --------------------------

SIKULIX_JAR="${SIKULIX_JAR:-$HOME/sikulixide-2.0.5-mac.jar}"
JAVA_BIN="${JAVA_HOME:+$JAVA_HOME/bin/java}"
JAVA_BIN="${JAVA_BIN:-java}"

# --- Preflight checks -------------------------------------------------------

if [[ ! -f "$SIKULIX_JAR" ]]; then
    echo "ERROR: SikuliX JAR not found at $SIKULIX_JAR" >&2
    echo "  Set SIKULIX_JAR to the correct path or place the JAR at the default location." >&2
    exit 1
fi

if ! command -v "$JAVA_BIN" &>/dev/null; then
    echo "ERROR: Java not found. Install Java 17+ or set JAVA_HOME." >&2
    exit 1
fi

# --- Run the SikuliX script -------------------------------------------------

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting daily export..."

"$JAVA_BIN" -jar "$SIKULIX_JAR" \
    -r "$SCRIPT_DIR/daily_export.py" \
    -- "$CONFIG_FILE"

EXIT_CODE=$?

if [[ $EXIT_CODE -eq 0 ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Daily export completed successfully."
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Daily export FAILED (exit code: $EXIT_CODE)." >&2
fi

# --- Trigger pipeline ingestion if macroclaw CLI is available ----------------

if command -v macroclaw &>/dev/null; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running one-shot import scan..."
    macroclaw watch --one-shot || true
fi

exit $EXIT_CODE

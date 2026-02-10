#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# MacroClaw -- Installation Script
#
# Installs the MacroClaw Python package, initializes the DuckDB database,
# and creates required data directories.  Safe to run multiple times
# (idempotent).
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default database path (can be overridden via MACROCLAW_DB_PATH)
DEFAULT_DB_PATH="${PROJECT_DIR}/data/macroclaw.duckdb"
DB_PATH="${MACROCLAW_DB_PATH:-${DEFAULT_DB_PATH}}"

# Colors for output (disabled when not a terminal)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BOLD='\033[1m'
    RESET='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BOLD=''
    RESET=''
fi

info()  { printf "${GREEN}[INFO]${RESET}  %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${RESET}  %s\n" "$*"; }
error() { printf "${RED}[ERROR]${RESET} %s\n" "$*" >&2; }
step()  { printf "\n${BOLD}==> %s${RESET}\n" "$*"; }

# ---------------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------------
step "Checking prerequisites"

MISSING=0

if ! command -v python3 &>/dev/null; then
    error "python3 is not installed or not on PATH."
    MISSING=1
else
    PYTHON_VERSION="$(python3 --version 2>&1)"
    info "Found ${PYTHON_VERSION}"
fi

if ! command -v java &>/dev/null; then
    warn "java is not installed or not on PATH."
    warn "Java is required for SikuliX automation but not for the core CLI."
    warn "Install it later with: brew install openjdk"
else
    JAVA_VERSION="$(java -version 2>&1 | head -1)"
    info "Found java: ${JAVA_VERSION}"
fi

if ! command -v pip3 &>/dev/null; then
    error "pip3 is not installed or not on PATH."
    MISSING=1
else
    info "Found pip3: $(pip3 --version 2>&1 | head -1)"
fi

if [ "${MISSING}" -ne 0 ]; then
    error "Missing required prerequisites.  Install them and re-run this script."
    exit 1
fi

# ---------------------------------------------------------------------------
# Install Python package in editable mode
# ---------------------------------------------------------------------------
step "Installing MacroClaw Python package"

pip3 install -e "${PROJECT_DIR}"
info "Python package installed in editable mode."

# ---------------------------------------------------------------------------
# Create data directories
# ---------------------------------------------------------------------------
step "Creating data directories"

DATA_DIRS=(
    "${PROJECT_DIR}/data"
    "${PROJECT_DIR}/data/imports"
    "${PROJECT_DIR}/data/archive"
    "${PROJECT_DIR}/data/exports"
    "${PROJECT_DIR}/data/screenshots"
)

for dir in "${DATA_DIRS[@]}"; do
    if [ ! -d "${dir}" ]; then
        mkdir -p "${dir}"
        info "Created ${dir}"
    else
        info "Already exists: ${dir}"
    fi
done

# ---------------------------------------------------------------------------
# Create config from example if it does not exist
# ---------------------------------------------------------------------------
step "Checking configuration"

CONFIG_FILE="${PROJECT_DIR}/config/macroclaw.yaml"
CONFIG_EXAMPLE="${PROJECT_DIR}/config/macroclaw.example.yaml"

if [ -f "${CONFIG_FILE}" ]; then
    info "Configuration already exists: ${CONFIG_FILE}"
elif [ -f "${CONFIG_EXAMPLE}" ]; then
    cp "${CONFIG_EXAMPLE}" "${CONFIG_FILE}"
    info "Created config from example: ${CONFIG_FILE}"
    warn "Review and edit ${CONFIG_FILE} before first use."
else
    info "No example config found.  Skipping config creation."
    info "The CLI will use defaults and environment variables."
fi

# ---------------------------------------------------------------------------
# Initialize DuckDB database
# ---------------------------------------------------------------------------
step "Initializing DuckDB database"

export MACROCLAW_DB_PATH="${DB_PATH}"

if [ -f "${DB_PATH}" ]; then
    info "Database already exists: ${DB_PATH}"
    info "Running schema migration to ensure tables are up to date."
fi

macroclaw init
info "Database initialized at: ${DB_PATH}"

# ---------------------------------------------------------------------------
# Summary and next steps
# ---------------------------------------------------------------------------
step "Installation complete"

info "MacroClaw has been installed successfully."
printf "\n"
printf "  Project directory : %s\n" "${PROJECT_DIR}"
printf "  Database path     : %s\n" "${DB_PATH}"
printf "  Config file       : %s\n" "${CONFIG_FILE:-<not created>}"
printf "\n"
printf "${BOLD}Next steps:${RESET}\n"
printf "\n"
printf "  1. Add to your shell profile (~/.zshrc or ~/.bashrc):\n"
printf "     export MACROCLAW_DB_PATH=\"%s\"\n" "${DB_PATH}"
printf "\n"
printf "  2. Set up the SikuliX daily export (requires Java):\n"
printf "     %s/scripts/setup_launchd.sh\n" "${PROJECT_DIR}"
printf "\n"
printf "  3. Capture SikuliX reference screenshots:\n"
printf "     Place them in %s/sikuli/images/\n" "${PROJECT_DIR}"
printf "\n"
printf "  4. Test the CLI:\n"
printf "     macroclaw status\n"
printf "     macroclaw summary\n"
printf "\n"

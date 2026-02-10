#!/usr/bin/env bash
# MacroClaw — Installation Script
# Installs the Python package, initializes the DuckDB database,
# and creates required data directories. Safe to run multiple times.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

DEFAULT_DB_PATH="${PROJECT_DIR}/data/macroclaw.duckdb"
DB_PATH="${MACROCLAW_DB_PATH:-${DEFAULT_DB_PATH}}"

if [ -t 1 ]; then
    GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; RESET='\033[0m'
else
    GREEN=''; YELLOW=''; RED=''; BOLD=''; RESET=''
fi

info()  { printf "${GREEN}[INFO]${RESET}  %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${RESET}  %s\n" "$*"; }
error() { printf "${RED}[ERROR]${RESET} %s\n" "$*" >&2; }
step()  { printf "\n${BOLD}==> %s${RESET}\n" "$*"; }

# Prerequisites
step "Checking prerequisites"

MISSING=0

if ! command -v python3 &>/dev/null; then
    error "python3 is not installed or not on PATH."
    MISSING=1
else
    info "Found $(python3 --version 2>&1)"
fi

if ! command -v pip3 &>/dev/null; then
    error "pip3 is not installed or not on PATH."
    MISSING=1
else
    info "Found pip3: $(pip3 --version 2>&1 | head -1)"
fi

if [ "${MISSING}" -ne 0 ]; then
    error "Missing required prerequisites."
    exit 1
fi

# Install Python package
step "Installing MacroClaw Python package"
pip3 install -e "${PROJECT_DIR}"
info "Installed in editable mode."

# Create data directories
step "Creating data directories"

for dir in "${PROJECT_DIR}/data" "${PROJECT_DIR}/data/imports" "${PROJECT_DIR}/data/archive"; do
    if [ ! -d "${dir}" ]; then
        mkdir -p "${dir}"
        info "Created ${dir}"
    else
        info "Already exists: ${dir}"
    fi
done

# Initialize DuckDB
step "Initializing DuckDB database"
export MACROCLAW_DB_PATH="${DB_PATH}"

if [ -f "${DB_PATH}" ]; then
    info "Database already exists: ${DB_PATH}"
fi

macroclaw init
info "Database initialized at: ${DB_PATH}"

# Done
step "Installation complete"

printf "\n"
printf "  Project directory : %s\n" "${PROJECT_DIR}"
printf "  Database path     : %s\n" "${DB_PATH}"
printf "\n"
printf "${BOLD}Next steps:${RESET}\n"
printf "\n"
printf "  1. Set your Anthropic API key:\n"
printf "     export ANTHROPIC_API_KEY=\"sk-ant-...\"\n"
printf "\n"
printf "  2. Test the AI export:\n"
printf "     macroclaw auto export-daily\n"
printf "\n"
printf "  3. Set up scheduled daily exports:\n"
printf "     %s/scripts/setup_launchd.sh\n" "${PROJECT_DIR}"
printf "\n"
printf "  4. Test the CLI:\n"
printf "     macroclaw status\n"
printf "     macroclaw summary\n"
printf "\n"

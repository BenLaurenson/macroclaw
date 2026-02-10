#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# MacroClaw -- launchd Setup Script
#
# Creates and installs launchd plist files for:
#   1. Daily SikuliX export (runs at 21:00 every day)
#   2. File watcher daemon (runs on user login)
#
# Usage:
#   ./setup_launchd.sh          Install and load launch agents
#   ./setup_launchd.sh --status Show current agent status
#
# To uninstall:
#   launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.macroclaw.daily-export.plist
#   launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.macroclaw.watcher.plist
#   rm ~/Library/LaunchAgents/com.macroclaw.daily-export.plist
#   rm ~/Library/LaunchAgents/com.macroclaw.watcher.plist
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
PLIST_SOURCE_DIR="${PROJECT_DIR}/config/launchd"

DAILY_EXPORT_LABEL="com.macroclaw.daily-export"
WATCHER_LABEL="com.macroclaw.watcher"

DAILY_EXPORT_PLIST="${DAILY_EXPORT_LABEL}.plist"
WATCHER_PLIST="${WATCHER_LABEL}.plist"

USER_ID="$(id -u)"

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
# Status mode
# ---------------------------------------------------------------------------
if [ "${1:-}" = "--status" ]; then
    step "LaunchAgent Status"
    printf "\n"

    for label in "${DAILY_EXPORT_LABEL}" "${WATCHER_LABEL}"; do
        printf "  %s: " "${label}"
        if launchctl print "gui/${USER_ID}/${label}" &>/dev/null; then
            printf "${GREEN}loaded${RESET}\n"
        else
            printf "${YELLOW}not loaded${RESET}\n"
        fi
    done

    printf "\n"
    exit 0
fi

# ---------------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------------
step "Checking prerequisites"

if [ ! -f "${PLIST_SOURCE_DIR}/${DAILY_EXPORT_PLIST}" ]; then
    error "Missing plist: ${PLIST_SOURCE_DIR}/${DAILY_EXPORT_PLIST}"
    error "Run this script from the MacroClaw project directory."
    exit 1
fi

if [ ! -f "${PLIST_SOURCE_DIR}/${WATCHER_PLIST}" ]; then
    error "Missing plist: ${PLIST_SOURCE_DIR}/${WATCHER_PLIST}"
    error "Run this script from the MacroClaw project directory."
    exit 1
fi

info "Source plists found in ${PLIST_SOURCE_DIR}"

# ---------------------------------------------------------------------------
# Ensure LaunchAgents directory exists
# ---------------------------------------------------------------------------
if [ ! -d "${LAUNCH_AGENTS_DIR}" ]; then
    mkdir -p "${LAUNCH_AGENTS_DIR}"
    info "Created ${LAUNCH_AGENTS_DIR}"
fi

# ---------------------------------------------------------------------------
# Install daily export plist
# ---------------------------------------------------------------------------
step "Installing ${DAILY_EXPORT_LABEL}"

DEST="${LAUNCH_AGENTS_DIR}/${DAILY_EXPORT_PLIST}"

# Unload existing agent if loaded
if launchctl print "gui/${USER_ID}/${DAILY_EXPORT_LABEL}" &>/dev/null; then
    warn "Agent already loaded.  Unloading before reinstall."
    launchctl bootout "gui/${USER_ID}/${DAILY_EXPORT_LABEL}" 2>/dev/null || true
fi

cp "${PLIST_SOURCE_DIR}/${DAILY_EXPORT_PLIST}" "${DEST}"
info "Copied plist to ${DEST}"

launchctl bootstrap "gui/${USER_ID}" "${DEST}"
info "Loaded ${DAILY_EXPORT_LABEL}"

# ---------------------------------------------------------------------------
# Install file watcher plist
# ---------------------------------------------------------------------------
step "Installing ${WATCHER_LABEL}"

DEST="${LAUNCH_AGENTS_DIR}/${WATCHER_PLIST}"

# Unload existing agent if loaded
if launchctl print "gui/${USER_ID}/${WATCHER_LABEL}" &>/dev/null; then
    warn "Agent already loaded.  Unloading before reinstall."
    launchctl bootout "gui/${USER_ID}/${WATCHER_LABEL}" 2>/dev/null || true
fi

cp "${PLIST_SOURCE_DIR}/${WATCHER_PLIST}" "${DEST}"
info "Copied plist to ${DEST}"

launchctl bootstrap "gui/${USER_ID}" "${DEST}"
info "Loaded ${WATCHER_LABEL}"

# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
step "Verifying installation"

FAILED=0

for label in "${DAILY_EXPORT_LABEL}" "${WATCHER_LABEL}"; do
    if launchctl print "gui/${USER_ID}/${label}" &>/dev/null; then
        info "${label} is running."
    else
        error "${label} failed to load."
        FAILED=1
    fi
done

if [ "${FAILED}" -ne 0 ]; then
    error "One or more agents failed to load.  Check logs with:"
    error "  log show --predicate 'subsystem == \"com.macroclaw\"' --last 5m"
    exit 1
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
step "Setup complete"

printf "\n"
printf "  Daily export : Runs at 21:00 every day\n"
printf "  File watcher : Runs on login, watches for new exports\n"
printf "\n"
printf "Check status any time with:\n"
printf "  %s/scripts/setup_launchd.sh --status\n" "${PROJECT_DIR}"
printf "\n"
printf "View logs with:\n"
printf "  tail -f /tmp/macroclaw-daily-export.log\n"
printf "  tail -f /tmp/macroclaw-watcher.log\n"
printf "\n"
printf "To uninstall:\n"
printf "  launchctl bootout gui/%s/%s\n" "${USER_ID}" "${DAILY_EXPORT_LABEL}"
printf "  launchctl bootout gui/%s/%s\n" "${USER_ID}" "${WATCHER_LABEL}"
printf "  rm %s/%s\n" "${LAUNCH_AGENTS_DIR}" "${DAILY_EXPORT_PLIST}"
printf "  rm %s/%s\n" "${LAUNCH_AGENTS_DIR}" "${WATCHER_PLIST}"
printf "\n"

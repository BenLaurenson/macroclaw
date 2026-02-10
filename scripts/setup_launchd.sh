#!/usr/bin/env bash
# MacroClaw — launchd Setup Script
#
# Installs launchd plist files for:
#   1. Daily AI-driven export (runs at 21:00 every day)
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

if [ -t 1 ]; then
    GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; RESET='\033[0m'
else
    GREEN=''; YELLOW=''; RED=''; BOLD=''; RESET=''
fi

info()  { printf "${GREEN}[INFO]${RESET}  %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${RESET}  %s\n" "$*"; }
error() { printf "${RED}[ERROR]${RESET} %s\n" "$*" >&2; }
step()  { printf "\n${BOLD}==> %s${RESET}\n" "$*"; }

# Status mode
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

# Prerequisites
step "Checking prerequisites"

for plist in "${DAILY_EXPORT_PLIST}" "${WATCHER_PLIST}"; do
    if [ ! -f "${PLIST_SOURCE_DIR}/${plist}" ]; then
        error "Missing plist: ${PLIST_SOURCE_DIR}/${plist}"
        exit 1
    fi
done

info "Source plists found in ${PLIST_SOURCE_DIR}"

[ ! -d "${LAUNCH_AGENTS_DIR}" ] && mkdir -p "${LAUNCH_AGENTS_DIR}"

# Install agents
for label in "${DAILY_EXPORT_LABEL}" "${WATCHER_LABEL}"; do
    plist="${label}.plist"
    dest="${LAUNCH_AGENTS_DIR}/${plist}"

    step "Installing ${label}"

    if launchctl print "gui/${USER_ID}/${label}" &>/dev/null; then
        warn "Already loaded. Unloading before reinstall."
        launchctl bootout "gui/${USER_ID}/${label}" 2>/dev/null || true
    fi

    cp "${PLIST_SOURCE_DIR}/${plist}" "${dest}"
    info "Copied plist to ${dest}"

    launchctl bootstrap "gui/${USER_ID}" "${dest}"
    info "Loaded ${label}"
done

# Verify
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
    error "One or more agents failed to load."
    exit 1
fi

step "Setup complete"

printf "\n"
printf "  Daily export : Runs at 21:00 (macroclaw auto export-daily)\n"
printf "  File watcher : Runs on login, watches for new exports\n"
printf "\n"
printf "Requires ANTHROPIC_API_KEY in your shell profile for AI exports.\n"
printf "\n"
printf "Check status:  %s/scripts/setup_launchd.sh --status\n" "${PROJECT_DIR}"
printf "View logs:     tail -f /tmp/macroclaw-daily-export.log\n"
printf "\n"

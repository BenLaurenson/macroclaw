# MacroClaw

Automated MacroFactor data pipeline. Exports nutrition and workout data from the MacroFactor iOS app (running on macOS), stores it in DuckDB, and exposes it via CLI.

Uses Claude Computer Use to visually navigate the app — no API access or jailbreaking required.

## Prerequisites

- macOS on Apple Silicon (13.0+)
- [MacroFactor](https://apps.apple.com/app/macrofactor-diet-tracker/id1609395984) installed from the App Store (iPhone app, runs via "Designed for iPhone")
- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/) with credits

## Setup

```bash
git clone git@github.com:BenLaurenson/macroclaw.git
cd macroclaw
pip3 install -e .
macroclaw init
```

Set your API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Usage

### AI-driven export (recommended)

Claude views screenshots of MacroFactor and clicks through the export flow automatically:

```bash
# Daily granular export
macroclaw auto export-daily

# Use a specific model
macroclaw auto export-daily --model claude-opus-4-6

# Free-form control
macroclaw auto run "Take a screenshot and describe what you see"
```

### Recorded sequence export (fallback)

Record a click sequence manually, then replay it:

```bash
# Record (click through the export flow, Ctrl+C to stop)
macroclaw auto record daily

# Replay
macroclaw auto daily
```

### Manual import

Seed the database from a MacroFactor all-time export or ingest a daily `.xlsx`:

```bash
macroclaw ingest ~/Downloads/MacroFactor-*.xlsx
```

Bulk (all-time) exports with multiple sheets are auto-detected and processed.

### Data queries

```bash
macroclaw summary              # Today's calories, macros, weight
macroclaw nutrition             # Detailed food log
macroclaw nutrition --date 2026-02-01
macroclaw workouts --days 7     # Exercise history
macroclaw weight --days 30      # Weight trend
macroclaw status                # Data freshness check
```

### File watcher

Auto-ingest any `.xlsx` dropped into `data/imports/`:

```bash
macroclaw watch
```

## Scheduling

Set up daily automated exports via launchd:

```bash
./scripts/setup_launchd.sh
```

This installs two launch agents:
- **Daily export** at 9 PM — runs `macroclaw auto export-daily`
- **File watcher** on login — auto-ingests new exports

Requires `ANTHROPIC_API_KEY` in your shell profile.

## Project Structure

```
macroclaw/
  automation/
    computer_use.py     # Claude Computer Use agent (screenshots + clicks)
    recorder.py         # Manual click sequence recorder/replayer
    export.py           # Export orchestration and download handling
    app.py              # macOS app control (open, close, focus)
    cli.py              # CLI commands for automation
  pipeline/
    schema.py           # DuckDB table definitions
    ingest.py           # XLSX parsing and loading
    queries.py          # Query functions (summary, nutrition, workouts, weight)
    watcher.py          # File watcher for auto-ingest
    cli.py              # CLI commands for data pipeline
  config/
    config.example.yaml # Example configuration
    launchd/            # launchd plist templates
  openclaw-skill/
    SKILL.md            # OpenClaw agent skill definition
  data/
    imports/            # Staging area for new exports
    archive/            # Processed exports
    macroclaw.duckdb    # Database (git-ignored)
```

## Configuration

```bash
cp config/config.example.yaml config/config.yaml
```

Key settings in `config/config.yaml`:

```yaml
macroclaw:
  db_path: "~/projects/macroclaw/data/macroclaw.duckdb"
  imports_dir: "~/projects/macroclaw/data/imports"
  archive_dir: "~/projects/macroclaw/data/archive"

computer_use:
  model: "claude-sonnet-4-5"
  max_iterations: 50
  download_timeout_daily: 30
  download_timeout_bulk: 120
```

## Cost

The AI export uses ~15 API calls per run with Sonnet 4.5. Estimated cost: **~$0.20/run** or **~$6/month** for daily exports.

## License

MIT

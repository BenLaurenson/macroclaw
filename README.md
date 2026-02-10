# MacroClaw

**Automated MacroFactor data pipeline for OpenClaw -- powered by SikuliX visual automation**

MacroClaw bridges the gap between MacroFactor's mobile-only nutrition and workout apps and your local data infrastructure. It uses SikuliX to visually automate the "Designed for iPhone" versions of MacroFactor running on Apple Silicon Macs, exports your data as `.xlsx` files, parses them into a DuckDB database, and exposes everything through an OpenClaw AI agent skill for natural language querying.

---

## Architecture

```
+---------------------+       +---------------------+       +------------------+
|   MacroFactor App   |       |  MacroFactor Workout |       |                  |
|  (iPhone on Mac)    |       |   (iPhone on Mac)    |       |   Scheduler      |
+----------+----------+       +----------+----------+       |   (cron/launchd) |
           |                             |                   +--------+---------+
           |  SikuliX visual automation  |                            |
           +-------------+--------------+                            |
                          |                                           |
                          v                                           |
                 +--------+--------+                                  |
                 |  sikuli/         |  <-------------------------------+
                 |  export.sikuli   |     triggers daily or bulk run
                 +--------+--------+
                          |
                    .xlsx files
                          |
                          v
                 +--------+--------+
                 |  data/imports/   |
                 |  (staging area)  |
                 +--------+--------+
                          |
                          v
                 +--------+--------+
                 |  scripts/        |
                 |  parse_xlsx.py   |
                 +--------+--------+
                          |
                          v
                 +--------+--------+
                 |  data/           |
                 |  macroclaw.duckdb|
                 +--------+--------+
                          |
                          v
                 +--------+--------+
                 |  OpenClaw Skill  |
                 |  (query agent)   |
                 +-----------------+
```

---

## Features

- **Visual GUI automation** -- SikuliX drives the MacroFactor and MacroFactor Workout apps through their native UI, requiring no API access or jailbreaking.
- **Daily scheduled exports** -- A lightweight cron or launchd job triggers a nightly export of the current day's nutrition log and workout data.
- **Bulk historical exports** -- A separate automation flow exports your full history for initial database seeding or periodic reconciliation.
- **XLSX parsing** -- Python scripts parse MacroFactor's exported spreadsheets, normalize the data, and load it into DuckDB.
- **DuckDB storage** -- All nutrition, macro, calorie, body weight, and workout data lives in a single portable DuckDB file with a well-defined schema.
- **OpenClaw integration** -- An OpenClaw agent skill lets you query your data with natural language (e.g., "What was my average protein intake last week?").
- **Idempotent imports** -- Re-importing the same export file will not create duplicate rows.
- **Archive management** -- Processed `.xlsx` files are moved to an archive directory with timestamps for auditability.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| macOS on Apple Silicon | 13.0+ | Required for "Designed for iPhone" app support |
| MacroFactor (nutrition) | Latest | Installed from the App Store as an iPhone app |
| MacroFactor Workout | Latest | Installed from the App Store as an iPhone app |
| Java (JDK or JRE) | 17+ | Required by SikuliX |
| SikuliX | 2.0.6 | Download the `sikulixide-2.0.6.jar` from the SikuliX releases page |
| Python | 3.11+ | For XLSX parsing and DuckDB loading |
| DuckDB | 1.0+ | Installed via `pip install duckdb` |
| OpenClaw | Latest | For the AI agent skill integration |

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-username/macroclaw.git
cd macroclaw
```

### 2. Install Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Set up SikuliX

Download `sikulixide-2.0.6.jar` and place it in the `sikuli/` directory:

```bash
curl -L -o sikuli/sikulixide-2.0.6.jar \
  https://launchpad.net/sikuli/sikulix/2.0.6/+download/sikulixide-2.0.6.jar
```

### 4. Capture reference screenshots

MacroClaw uses image-based matching, so you must capture your own reference screenshots on your specific machine. Screen resolution, dark/light mode, and macOS appearance settings all affect matching.

```bash
# Launch SikuliX IDE to capture screenshots
java -jar sikuli/sikulixide-2.0.6.jar
```

Open `sikuli/export.sikuli` in the IDE and follow the instructions in the script comments to capture each required UI element. Save the `.png` files into `sikuli/images/`.

See the [Image Capture Guide](#capturing-reference-screenshots) in the Troubleshooting section for detailed instructions.

### 5. Copy and edit the configuration file

```bash
cp config/config.example.yaml config/config.yaml
```

Edit `config/config.yaml` to set your paths and preferences.

### 6. Run a test export

```bash
# Make sure MacroFactor is open and visible on screen
python3 scripts/run_export.py --mode daily --dry-run
```

Remove `--dry-run` when you are satisfied that the automation is targeting the correct UI elements.

### 7. Set up the scheduled job

```bash
# Install the launchd plist for daily exports at 11:30 PM
cp config/com.macroclaw.daily-export.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.macroclaw.daily-export.plist
```

### 8. Register the OpenClaw skill

```bash
openclaw skill register ./skills/macroclaw_query.py
```

---

## How It Works

MacroClaw performs two types of automated exports:

### Daily Export

The daily export flow runs once per day (typically late evening) and captures the current day's data:

1. **Launch** -- The scheduler triggers `scripts/run_export.py --mode daily`.
2. **Activate app** -- SikuliX brings the MacroFactor app to the foreground.
3. **Navigate to export** -- SikuliX clicks through the app's menu: Profile > Settings > Export Data > Today.
4. **Save file** -- The export dialog is automated to save the `.xlsx` file to `data/imports/`.
5. **Repeat for workout** -- The same flow runs against MacroFactor Workout.
6. **Parse and load** -- `parse_xlsx.py` reads the new files, transforms the data, and inserts it into DuckDB.
7. **Archive** -- Processed `.xlsx` files are moved to `data/archive/` with a timestamp prefix.

### Bulk Export

The bulk export is used for initial setup or periodic full reconciliation:

1. **Launch** -- Run `scripts/run_export.py --mode bulk`.
2. **Full history export** -- SikuliX navigates to the export screen and selects "All Data" instead of a single day.
3. **Parse with upsert** -- The parser uses an upsert strategy to merge historical data without creating duplicates.
4. **Verification** -- Row counts and date ranges are logged for manual verification.

---

## Data Flow

```
MacroFactor App                MacroFactor Workout App
       |                                |
       v                                v
  nutrition_export.xlsx           workout_export.xlsx
       |                                |
       +----------------+---------------+
                        |
                        v
              parse_xlsx.py
                        |
          +-------------+-------------+
          |             |             |
          v             v             v
    daily_nutrition  daily_weight  workouts
      (table)         (table)      (table)
          |             |             |
          +-------------+-------------+
                        |
                        v
              macroclaw.duckdb
                        |
                        v
              OpenClaw Agent Skill
```

### DuckDB Schema Overview

**daily_nutrition** -- One row per day with columns for calories, protein (g), carbs (g), fat (g), fiber (g), and any custom-tracked micros.

**daily_weight** -- One row per day with body weight in the user's configured unit.

**workouts** -- One row per exercise set with columns for date, exercise name, sets, reps, weight, RPE, and notes.

---

## OpenClaw Skill Usage

Once registered, the MacroClaw skill enables natural language queries against your nutrition and workout data. Examples:

```
> What was my average daily protein intake over the last 30 days?

Your average daily protein intake over the last 30 days was 187g,
with a range of 142g to 231g.

> Show me my weekly calorie averages for January 2026.

Week of Jan 1:  2,410 kcal/day
Week of Jan 8:  2,385 kcal/day
Week of Jan 15: 2,520 kcal/day
Week of Jan 22: 2,490 kcal/day
Week of Jan 29: 2,455 kcal/day

> How has my bench press progressed over the last 3 months?

Bench Press estimated 1RM trend (Nov 2025 - Jan 2026):
  Nov: 225 lbs
  Dec: 230 lbs
  Jan: 237 lbs
  Trend: +5.3% over 3 months

> On which days last week did I miss my protein target?

You missed your protein target on 2 of 7 days:
  - Tuesday, Feb 3: 148g (target: 180g, deficit: 32g)
  - Saturday, Feb 7: 155g (target: 180g, deficit: 25g)
```

The skill translates natural language into SQL queries against the DuckDB database and formats the results for readability.

---

## Configuration

All configuration lives in `config/config.yaml`. Copy `config/config.example.yaml` to get started.

### Key settings

```yaml
# Path to the SikuliX JAR file
sikulix_jar: sikuli/sikulixide-2.0.6.jar

# Path to reference screenshot images
image_dir: sikuli/images/

# Where exported .xlsx files are saved
import_dir: data/imports/

# Where processed files are archived
archive_dir: data/archive/

# DuckDB database file
database: data/macroclaw.duckdb

# Image match similarity threshold (0.0 to 1.0)
# Lower values are more forgiving but risk false matches.
# Default of 0.85 works well for Retina displays.
match_similarity: 0.85

# Timeout in seconds to wait for UI elements to appear
wait_timeout: 10

# Export mode: "daily" or "bulk"
default_mode: daily

# Whether to archive processed files (true/false)
archive_exports: true

# Logging level: DEBUG, INFO, WARNING, ERROR
log_level: INFO
```

---

## Troubleshooting

### The screen must be unlocked

SikuliX operates by taking screenshots and matching against reference images. If your Mac's screen is locked, sleep, or has a screensaver active, the automation will fail. Ensure that:

- The screen is awake and unlocked when the scheduled job runs.
- Energy Saver settings prevent the display from sleeping during the export window.
- You may want to use `caffeinate` in your launchd plist to prevent sleep during the job.

### Image matching failures

If SikuliX cannot find a UI element, the most common causes are:

1. **Resolution mismatch** -- Reference screenshots were captured at a different display resolution or scaling factor. Always capture on the same display where the automation will run.
2. **Dark mode vs. light mode** -- If you switch between modes, you need two sets of reference images or must standardize on one.
3. **App updates** -- MacroFactor UI updates can change button styles, colors, or layouts. Re-capture affected screenshots after app updates.
4. **Similarity threshold** -- If matching is too strict, lower `match_similarity` in your config. If it is producing false matches, raise it.

### Capturing reference screenshots

To capture or re-capture reference screenshots:

1. Open the SikuliX IDE:
   ```bash
   java -jar sikuli/sikulixide-2.0.6.jar
   ```
2. Use the IDE's screenshot capture tool (camera icon) to select UI elements.
3. Capture each button, menu item, and dialog element listed in `sikuli/export.sikuli` comments.
4. Save images to `sikuli/images/` with the names specified in the script (e.g., `btn_export.png`, `menu_settings.png`).
5. Test the automation with `--dry-run` before enabling scheduled runs.

### Common error messages

| Error | Cause | Fix |
|---|---|---|
| `FindFailed: btn_export.png` | SikuliX could not locate the export button | Re-capture `btn_export.png` or lower `match_similarity` |
| `TimeoutError: App not responding` | MacroFactor did not open within the timeout | Increase `wait_timeout` or ensure the app is installed |
| `FileNotFoundError: sikulixide-2.0.6.jar` | SikuliX JAR not found | Download and place it in `sikuli/` per the Quick Start guide |
| `DuckDBError: UNIQUE constraint` | Attempted duplicate insert | This should not happen with idempotent imports; check `parse_xlsx.py` logic |

### Logs

Logs are written to `logs/macroclaw.log` and rotated daily. Increase the log level to `DEBUG` in your config for verbose output when diagnosing issues.

---

## Project Structure

```
macroclaw/
  config/
    config.example.yaml     # Example configuration (committed)
    config.yaml             # Your local configuration (git-ignored)
    com.macroclaw.daily-export.plist  # launchd plist for scheduling
  data/
    imports/                # Staging area for new .xlsx exports
    archive/                # Processed .xlsx files (timestamped)
    macroclaw.duckdb        # DuckDB database file
  logs/
    macroclaw.log           # Application log
  scripts/
    run_export.py           # Main entry point for export automation
    parse_xlsx.py           # XLSX parser and DuckDB loader
    schema.sql              # DuckDB schema definitions
  sikuli/
    export.sikuli/          # SikuliX automation script
    images/                 # Reference screenshots (user-captured, git-ignored)
    sikulixide-2.0.6.jar    # SikuliX IDE JAR (downloaded, git-ignored)
  skills/
    macroclaw_query.py      # OpenClaw agent skill
  tests/
    test_parse_xlsx.py      # Unit tests for the parser
    test_schema.py          # Schema validation tests
  .gitignore
  CONTRIBUTING.md
  LICENSE
  README.md
  requirements.txt
```

---

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a pull request.

---

## License

MacroClaw is released under the [MIT License](LICENSE).

Copyright 2026 MacroClaw Contributors.

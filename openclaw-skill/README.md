# MacroClaw OpenClaw Skill

This directory contains the OpenClaw skill definition for MacroClaw, a fitness
data pipeline that ingests daily MacroFactor exports and makes them queryable
through a conversational interface.

## Prerequisites

- Python 3.11 or later
- Java runtime (for SikuliX automation)
- The MacroClaw CLI installed (`pip3 install -e ~/projects/macroclaw`)
- A DuckDB database initialized with `macroclaw init`

## Installation

### 1. Install MacroClaw

Run the project installation script:

```bash
~/projects/macroclaw/scripts/install.sh
```

This installs the Python package in editable mode, initializes the database, and
creates the required data directories.

### 2. Set Environment Variables

Add the following to your shell profile (`~/.zshrc`, `~/.bashrc`, or equivalent):

```bash
export MACROCLAW_DB_PATH="$HOME/projects/macroclaw/data/macroclaw.duckdb"
```

Reload your shell or run `source ~/.zshrc` after editing.

### 3. Register the Skill in OpenClaw

Copy or symlink the skill directory into your OpenClaw skills path:

```bash
# If OpenClaw looks for skills in ~/.openclaw/skills/
ln -s ~/projects/macroclaw/openclaw-skill ~/.openclaw/skills/macroclaw
```

Or register it directly if OpenClaw supports a registration command:

```bash
openclaw skill install ~/projects/macroclaw/openclaw-skill
```

### 4. Verify the Installation

Run a quick check to make sure everything works:

```bash
# Verify the CLI is available
macroclaw status

# Verify the database exists
ls -la "$MACROCLAW_DB_PATH"

# Verify the skill is loaded
openclaw skill list | grep -i macroclaw
```

## Environment Variables

| Variable            | Required | Description                                      |
|---------------------|----------|--------------------------------------------------|
| `MACROCLAW_DB_PATH` | Yes      | Absolute path to the DuckDB database file.       |

## Testing the Skill

After installation, test each command to confirm data flows correctly:

```bash
# Initialize the database if not done already
macroclaw init

# Check system status
macroclaw status

# Import sample data (if available)
macroclaw import ~/projects/macroclaw/tests/sample_data/

# Run a summary
macroclaw summary
```

## Example Conversations

Below are example interactions showing how the skill responds to natural
language queries.

### Daily Summary

```
User: health summary

Assistant: Here is your daily summary for 2026-02-10:

| Metric       | Actual | Target |    % |
|--------------|-------:|-------:|-----:|
| Calories     |  2,150 |  2,300 |  93% |
| Protein (g)  |    182 |    190 |  96% |
| Carbs (g)    |    240 |    260 |  92% |
| Fat (g)      |     68 |     72 |  94% |

Weight: 185.2 lbs (trend: 184.8 lbs)

Today's workout: Upper Body Push -- 6 exercises, 45 min
```

### Nutrition Query

```
User: what did I eat yesterday

Assistant: Here is your nutrition log for 2026-02-09:

**Breakfast**
| Food            | Calories | Protein | Carbs | Fat |
|-----------------|----------|---------|-------|-----|
| Oatmeal         |      300 |    10 g |  54 g | 6 g |
| Protein shake   |      160 |    30 g |   4 g | 2 g |
| Banana          |      105 |     1 g |  27 g | 0 g |

**Lunch**
| Food            | Calories | Protein | Carbs | Fat |
|-----------------|----------|---------|-------|-----|
| Chicken breast  |      280 |    52 g |   0 g | 6 g |
| Brown rice      |      215 |     5 g |  45 g | 2 g |
| Mixed greens    |       45 |     3 g |   7 g | 1 g |

**Totals: 2,150 cal | 182 g protein | 240 g carbs | 68 g fat**
```

### Weight Trend

```
User: show my weight

Assistant: Here is your weight trend for the last 30 days:

| Week       | Avg Scale (lbs) | Avg Trend (lbs) | Change |
|------------|----------------:|----------------:|-------:|
| Feb 03-09  |           185.4 |           184.9 |  -0.3  |
| Jan 27-Feb 02 |        185.7 |           185.2 |  -0.4  |
| Jan 20-26  |           186.1 |           185.6 |  -0.5  |
| Jan 13-19  |           186.6 |           186.1 |  -0.2  |

Trend: losing at approximately 0.35 lbs/week.
Current trend weight: 184.8 lbs.
```

### Workout Log

```
User: how was my workout

Assistant: Here is your most recent workout (2026-02-10 -- Upper Body Push, 45 min):

| Exercise         | Set | Reps | Weight (lbs) | Notes |
|------------------|----:|-----:|-------------:|-------|
| Bench Press      |   1 |    8 |          185 |       |
| Bench Press      |   2 |    8 |          185 |       |
| Bench Press      |   3 |    7 |          185 |       |
| OHP              |   1 |   10 |           95 | [PR]  |
| OHP              |   2 |    9 |           95 |       |
| OHP              |   3 |    8 |           95 |       |
| Incline DB Press |   1 |   12 |           55 |       |
| Incline DB Press |   2 |   11 |           55 |       |
| Incline DB Press |   3 |   10 |           55 |       |

Notable: OHP 10 reps at 95 lbs is a new rep PR.
```


---
name: macroclaw
description: Query and display nutrition, workout, and weight-tracking data from the MacroClaw pipeline. Use when user asks about food intake, macros, workouts, body weight, or fitness progress.
metadata: {"clawdbot":{"emoji":"💪","requires":{"bins":["macroclaw"],"env":["MACROCLAW_DB_PATH"]},"install":"pip3 install -e ~/projects/macroclaw"}}
---

# MacroClaw - Fitness Dashboard

Query and display nutrition, workout, and weight-tracking data from the MacroClaw
pipeline.  MacroClaw ingests daily exports from MacroFactor (via Claude Computer
Use AI automation) into a local DuckDB database and exposes the data through a CLI.
Use this skill whenever the user asks about their food intake, macronutrient
adherence, workout history, body-weight trends, or overall fitness progress.

## Trigger Phrases

- health summary
- nutrition today
- workout log
- weight trend
- macro check
- fitness report
- how were my macros
- what did I eat
- how was my workout
- show my weight

## Commands

### summary / daily summary

Run the daily summary command and present the results in a clean, readable format.

```
macroclaw summary
```

Show today's calorie and macronutrient totals versus targets, workout synopsis,
and current weight/trend.

### nutrition [date]

Show the detailed food log for a given date (defaults to today).

```
macroclaw nutrition --date DATE
```

- `DATE` is in `YYYY-MM-DD` format.  Omit the flag entirely for today.
- Present each meal as a sub-table with per-item macros.
- Always include a totals row and show the delta against targets.

### workouts [days]

Show exercise history for the last N days (defaults to 7).

```
macroclaw workouts --days N
```

- Group output by date and workout name.
- List exercises with sets, reps, and weight.
- Highlight any personal records (PRs) if detected.

### weight [days]

Show weight trend over the last N days (defaults to 30).

```
macroclaw weight --days N
```

- Display both the raw scale weight and the smoothed trend weight.
- Calculate and show weekly averages.
- Note the direction (gaining, losing, maintaining) and rate of change.

### macro check

Calculate macronutrient adherence percentages for the current day.

```
macroclaw summary
```

Parse the summary output and compute adherence as a percentage of target for
each macro: protein, calories, carbohydrates, and fat.  Flag any that are
significantly over or under target (more than 10% deviation).

### fitness report

Generate a comprehensive weekly report combining nutrition, workout, and weight
data.

```
macroclaw summary
macroclaw nutrition --date <each day of the past 7 days>
macroclaw workouts --days 7
macroclaw weight --days 7
```

Aggregate the data into sections:

1. **Nutrition overview** -- average daily calories, protein, carbs, fat vs targets.
2. **Training overview** -- number of sessions, total volume, notable PRs.
3. **Weight overview** -- start/end weight, net change, trend direction.

### sync / force export

Manually trigger the AI-driven export.

```
source ~/.config/clawdbot/env && /Users/ben/Library/Python/3.11/bin/macroclaw auto export-daily --model claude-sonnet-4-5
```

Use this when the user explicitly requests a fresh data pull from MacroFactor.
After the export completes, re-run `macroclaw summary` to confirm new data
arrived.

### status

Check system health and data freshness.

```
macroclaw status
```

Display the last successful import timestamp and flag whether data is stale
(older than 24 hours).

## Implementation Notes

1. **Execution**: Use the exec tool to run `macroclaw` CLI commands.  The CLI is
   installed as a Python console script via `pip3 install -e ~/projects/macroclaw`
   and reads the database path from the `MACROCLAW_DB_PATH` environment variable.

2. **Formatting**: Always format output as clean Markdown tables.  Use alignment
   and separators so the data is easy to scan.

3. **Nutrition presentation**: When showing nutrition data, always display actual
   values alongside targets and the percentage of target hit.  Example column
   headers: `Actual | Target | %`.

4. **Workout presentation**: When showing workout data, highlight any set where
   the weight or reps exceed the previous best for that exercise.  Mark these
   rows with `[PR]`.

5. **Weight presentation**: Always show both the raw scale weight and the
   exponentially-smoothed trend weight.  The trend weight reduces noise from
   day-to-day water fluctuations and is the more meaningful number.

6. **Staleness warning**: Before presenting any data, check the `status` output.
   If the most recent import is older than 24 hours, prepend a warning to the
   response:
   ```
   WARNING: Data was last imported on YYYY-MM-DD HH:MM.
   Run "sync" to pull fresh data from MacroFactor.
   ```

7. **Error handling**: If a CLI command exits with a non-zero status, show the
   stderr output and suggest common fixes (database not initialized, missing
   environment variable, stale exports).

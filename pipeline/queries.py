"""Query functions for retrieving data from the MacroClaw database.

All functions accept an open ``duckdb.DuckDBPyConnection`` and return plain
Python dicts or lists of dicts for easy JSON serialization.
"""

import logging
from datetime import date, timedelta

import duckdb

logger = logging.getLogger(__name__)


def _rows_to_dicts(result: duckdb.DuckDBPyRelation | None) -> list[dict]:
    """Convert a DuckDB query result to a list of dicts.

    Handles the case where the result is ``None`` (no rows) by returning
    an empty list.
    """
    if result is None:
        return []
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


# ---------------------------------------------------------------------------
# Public query functions
# ---------------------------------------------------------------------------


def get_daily_summary(db: duckdb.DuckDBPyConnection, date_str: str) -> dict:
    """Return all daily summary metrics for a given date.

    Args:
        db: Open DuckDB connection.
        date_str: Date string in ``YYYY-MM-DD`` format.

    Returns:
        A dict with summary fields, or an empty dict if no data exists.
    """
    result = db.execute(
        "SELECT * FROM daily_summary WHERE date = ? LIMIT 1", [date_str]
    )
    rows = _rows_to_dicts(result)
    if rows:
        row = rows[0]
        # Stringify date for JSON
        if isinstance(row.get("date"), date):
            row["date"] = row["date"].isoformat()
        return row
    return {}


def get_nutrition_log(db: duckdb.DuckDBPyConnection, date_str: str) -> list[dict]:
    """Return all food entries for a given date, ordered by meal.

    Args:
        db: Open DuckDB connection.
        date_str: Date string in ``YYYY-MM-DD`` format.

    Returns:
        A list of dicts, one per food entry.
    """
    result = db.execute(
        "SELECT * FROM nutrition_log WHERE date = ? ORDER BY meal, food_name",
        [date_str],
    )
    rows = _rows_to_dicts(result)
    for row in rows:
        if isinstance(row.get("date"), date):
            row["date"] = row["date"].isoformat()
    return rows


def get_workouts(
    db: duckdb.DuckDBPyConnection,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """Return workout details within a date range.

    Args:
        db: Open DuckDB connection.
        start_date: Start date (inclusive) in ``YYYY-MM-DD`` format.
        end_date: End date (inclusive) in ``YYYY-MM-DD`` format.

    Returns:
        A list of dicts ordered by date, exercise, and set number.
    """
    result = db.execute(
        "SELECT * FROM workouts WHERE date BETWEEN ? AND ? "
        "ORDER BY date, exercise_name, set_number",
        [start_date, end_date],
    )
    rows = _rows_to_dicts(result)
    for row in rows:
        if isinstance(row.get("date"), date):
            row["date"] = row["date"].isoformat()
    return rows


def get_weight_trend(
    db: duckdb.DuckDBPyConnection,
    days: int = 30,
) -> list[dict]:
    """Return weight log entries for the most recent *days* days.

    Args:
        db: Open DuckDB connection.
        days: Number of days to look back from today.

    Returns:
        A list of dicts ordered by date ascending.
    """
    start = (date.today() - timedelta(days=days)).isoformat()
    result = db.execute(
        "SELECT * FROM weight_log WHERE date >= ? ORDER BY date ASC", [start]
    )
    rows = _rows_to_dicts(result)
    for row in rows:
        if isinstance(row.get("date"), date):
            row["date"] = row["date"].isoformat()
    return rows


def get_macro_adherence(
    db: duckdb.DuckDBPyConnection,
    days: int = 7,
) -> dict:
    """Return average actuals vs targets for the last *days* days.

    Args:
        db: Open DuckDB connection.
        days: Number of days to look back from today.

    Returns:
        A dict with ``avg_calories``, ``avg_protein_g``, ``avg_carbs_g``,
        ``avg_fat_g``, ``avg_calorie_target``, ``avg_protein_target_g``,
        ``days_tracked``, and ``adherence_pct`` (calories actual / target).
    """
    start = (date.today() - timedelta(days=days)).isoformat()
    result = db.execute(
        """
        SELECT
            COUNT(*)                    AS days_tracked,
            AVG(total_calories)         AS avg_calories,
            AVG(total_protein_g)        AS avg_protein_g,
            AVG(total_carbs_g)          AS avg_carbs_g,
            AVG(total_fat_g)            AS avg_fat_g,
            AVG(calorie_target)         AS avg_calorie_target,
            AVG(protein_target_g)       AS avg_protein_target_g
        FROM daily_summary
        WHERE date >= ?
        """,
        [start],
    )
    rows = _rows_to_dicts(result)
    if not rows or rows[0]["days_tracked"] == 0:
        return {"days_tracked": 0}

    data = rows[0]
    # Compute adherence percentage (actual / target * 100)
    if data.get("avg_calorie_target") and data["avg_calorie_target"] > 0:
        data["adherence_pct"] = round(
            (data["avg_calories"] / data["avg_calorie_target"]) * 100, 1
        )
    else:
        data["adherence_pct"] = None

    # Round floats for readability
    for key in ["avg_calories", "avg_protein_g", "avg_carbs_g", "avg_fat_g",
                "avg_calorie_target", "avg_protein_target_g"]:
        if data.get(key) is not None:
            data[key] = round(data[key], 1)

    return data


def get_recent_prs(
    db: duckdb.DuckDBPyConnection,
    days: int = 30,
) -> list[dict]:
    """Return personal records (max weight per exercise) within the last *days* days.

    A "PR" here means the heaviest single set recorded for each exercise
    in the specified window.

    Args:
        db: Open DuckDB connection.
        days: Number of days to look back from today.

    Returns:
        A list of dicts with ``exercise_name``, ``max_weight_kg``,
        ``reps_at_max``, and ``date``.
    """
    start = (date.today() - timedelta(days=days)).isoformat()
    result = db.execute(
        """
        WITH ranked AS (
            SELECT
                exercise_name,
                weight_kg,
                reps,
                date,
                ROW_NUMBER() OVER (
                    PARTITION BY exercise_name
                    ORDER BY weight_kg DESC, reps DESC
                ) AS rn
            FROM workouts
            WHERE date >= ?
              AND weight_kg IS NOT NULL
        )
        SELECT
            exercise_name,
            weight_kg   AS max_weight_kg,
            reps         AS reps_at_max,
            date
        FROM ranked
        WHERE rn = 1
        ORDER BY max_weight_kg DESC
        """,
        [start],
    )
    rows = _rows_to_dicts(result)
    for row in rows:
        if isinstance(row.get("date"), date):
            row["date"] = row["date"].isoformat()
    return rows

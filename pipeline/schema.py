"""DuckDB schema setup for the MacroClaw data pipeline.

Creates and manages the database schema used to store MacroFactor export data
including nutrition logs, workouts, weight tracking, and daily summaries.
"""

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQL statements
# ---------------------------------------------------------------------------

_CREATE_NUTRITION_LOG = """
CREATE TABLE IF NOT EXISTS nutrition_log (
    date            DATE NOT NULL,
    meal            TEXT NOT NULL,
    calories        DOUBLE,
    protein_g       DOUBLE,
    carbs_g         DOUBLE,
    fat_g           DOUBLE,
    fiber_g         DOUBLE,
    sodium_mg       DOUBLE,
    food_name       TEXT,
    food_details    TEXT,       -- JSON text for extra fields
    source          TEXT,
    imported_at     TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (date, meal, food_name)
);
"""

_CREATE_WORKOUTS = """
CREATE TABLE IF NOT EXISTS workouts (
    date            DATE NOT NULL,
    workout_name    TEXT,
    duration_min    DOUBLE,
    exercise_name   TEXT NOT NULL,
    set_number      INTEGER NOT NULL,
    reps            INTEGER,
    weight_kg       DOUBLE,
    rpe             DOUBLE,
    notes           TEXT,
    source          TEXT,
    imported_at     TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (date, exercise_name, set_number)
);
"""

_CREATE_WEIGHT_LOG = """
CREATE TABLE IF NOT EXISTS weight_log (
    date                DATE PRIMARY KEY,
    scale_weight_kg     DOUBLE,
    trend_weight_kg     DOUBLE,
    source              TEXT,
    imported_at         TIMESTAMP DEFAULT current_timestamp
);
"""

_CREATE_DAILY_SUMMARY = """
CREATE TABLE IF NOT EXISTS daily_summary (
    date                DATE PRIMARY KEY,
    total_calories      DOUBLE,
    total_protein_g     DOUBLE,
    total_carbs_g       DOUBLE,
    total_fat_g         DOUBLE,
    calorie_target      DOUBLE,
    protein_target_g    DOUBLE,
    expenditure_kcal    DOUBLE,
    source              TEXT,
    imported_at         TIMESTAMP DEFAULT current_timestamp
);
"""

_CREATE_EXPORT_HISTORY = """
CREATE SEQUENCE IF NOT EXISTS export_history_id_seq;

CREATE TABLE IF NOT EXISTS export_history (
    id              BIGINT DEFAULT nextval('export_history_id_seq') PRIMARY KEY,
    export_type     TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    file_hash       TEXT NOT NULL,
    rows_imported   INTEGER DEFAULT 0,
    imported_at     TIMESTAMP DEFAULT current_timestamp
);
"""

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_nutrition_log_date ON nutrition_log (date);",
    "CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts (date);",
    "CREATE INDEX IF NOT EXISTS idx_weight_log_date ON weight_log (date);",
    "CREATE INDEX IF NOT EXISTS idx_daily_summary_date ON daily_summary (date);",
    "CREATE INDEX IF NOT EXISTS idx_export_history_hash ON export_history (file_hash);",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def init_db(db_path: str) -> duckdb.DuckDBPyConnection:
    """Create or connect to the MacroClaw DuckDB database and ensure all tables exist.

    Args:
        db_path: Filesystem path for the DuckDB database file.
                 Parent directories are created automatically.

    Returns:
        An open ``duckdb.DuckDBPyConnection`` ready for use.
    """
    db_path = str(Path(db_path).expanduser().resolve())
    parent = Path(db_path).parent
    parent.mkdir(parents=True, exist_ok=True)

    logger.info("Connecting to database at %s", db_path)
    conn = duckdb.connect(db_path)

    for ddl in [
        _CREATE_NUTRITION_LOG,
        _CREATE_WORKOUTS,
        _CREATE_WEIGHT_LOG,
        _CREATE_DAILY_SUMMARY,
        _CREATE_EXPORT_HISTORY,
    ]:
        conn.execute(ddl)

    for idx in _INDEXES:
        conn.execute(idx)

    logger.info("Database schema initialized successfully")
    return conn

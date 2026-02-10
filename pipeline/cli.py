"""Click CLI for the MacroClaw data pipeline.

Provides commands for database initialization, manual ingestion, file
watching, and data queries.  All output goes to stdout and logging goes
to stderr so the two streams can be handled independently.
"""

import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

import click
import yaml

from pipeline.ingest import ingest_xlsx
from pipeline.queries import (
    get_daily_summary,
    get_macro_adherence,
    get_nutrition_log,
    get_recent_prs,
    get_weight_trend,
    get_workouts,
)
from pipeline.schema import init_db
from pipeline.watcher import watch

logger = logging.getLogger("macroclaw")

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG_LOCATIONS = [
    Path("./config/config.yaml"),
    Path("./config.yaml"),
    Path("~/.config/macroclaw/config.yaml"),
]

_DEFAULTS = {
    "db_path": "~/projects/macroclaw/data/macroclaw.duckdb",
    "imports_dir": "~/projects/macroclaw/data/imports",
    "archive_dir": "~/projects/macroclaw/data/archive",
}


def _load_config(config_path: str | None) -> dict:
    """Load configuration from a YAML file, falling back to defaults.

    Searches several conventional locations when *config_path* is ``None``.
    """
    if config_path:
        p = Path(config_path).expanduser().resolve()
        if p.exists():
            with open(p) as f:
                data = yaml.safe_load(f) or {}
            return data.get("macroclaw", data)

    for loc in _DEFAULT_CONFIG_LOCATIONS:
        p = loc.expanduser().resolve()
        if p.exists():
            with open(p) as f:
                data = yaml.safe_load(f) or {}
            return data.get("macroclaw", data)

    return dict(_DEFAULTS)


def _resolve(cfg: dict, key: str) -> str:
    """Resolve a config value, expanding ``~`` and using the built-in default."""
    return str(Path(cfg.get(key, _DEFAULTS[key])).expanduser().resolve())


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
@click.option(
    "--config", "config_path", default=None, type=click.Path(),
    help="Path to config.yaml (auto-detected if omitted).",
)
@click.option(
    "--verbose", "-v", is_flag=True, default=False,
    help="Enable debug-level logging.",
)
@click.pass_context
def cli(ctx: click.Context, config_path: str | None, verbose: bool) -> None:
    """MacroClaw -- automated MacroFactor data pipeline."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    ctx.ensure_object(dict)
    ctx.obj["cfg"] = _load_config(config_path)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@cli.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize the DuckDB database and create all tables."""
    cfg = ctx.obj["cfg"]
    db_path = _resolve(cfg, "db_path")
    conn = init_db(db_path)
    conn.close()
    click.echo(f"Database initialized at {db_path}")


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--type", "export_type", default=None,
    type=click.Choice(["nutrition", "workout", "weight", "summary"]),
    help="Override auto-detection of export type.",
)
@click.pass_context
def ingest(ctx: click.Context, file: str, export_type: str | None) -> None:
    """Manually ingest a MacroFactor .xlsx export."""
    cfg = ctx.obj["cfg"]
    db_path = _resolve(cfg, "db_path")
    archive_dir = _resolve(cfg, "archive_dir")

    stats = ingest_xlsx(
        db_path=db_path,
        xlsx_path=file,
        export_type=export_type,
        archive_dir=archive_dir,
    )
    if stats["skipped"]:
        click.echo(f"Skipped (already imported): {file}")
    else:
        click.echo(
            f"Imported {stats['rows_imported']} rows "
            f"({stats['export_type']}) from {file}"
        )


@cli.command("watch")
@click.option("--one-shot", is_flag=True, default=False, help="Process existing files and exit.")
@click.pass_context
def watch_cmd(ctx: click.Context, one_shot: bool) -> None:
    """Start the file-system watcher daemon (or one-shot scan)."""
    cfg = ctx.obj["cfg"]
    watch(
        db_path=_resolve(cfg, "db_path"),
        imports_dir=_resolve(cfg, "imports_dir"),
        archive_dir=_resolve(cfg, "archive_dir"),
        one_shot=one_shot,
    )


@cli.command()
@click.option("--date", "date_str", default=None, help="Date (YYYY-MM-DD). Defaults to today.")
@click.pass_context
def summary(ctx: click.Context, date_str: str | None) -> None:
    """Print the daily summary for a given date."""
    cfg = ctx.obj["cfg"]
    db_path = _resolve(cfg, "db_path")
    target_date = date_str or date.today().isoformat()

    conn = init_db(db_path)
    data = get_daily_summary(conn, target_date)
    conn.close()

    if not data:
        click.echo(f"No summary data for {target_date}")
        return
    click.echo(json.dumps(data, indent=2, default=str))


@cli.command()
@click.option("--date", "date_str", default=None, help="Date (YYYY-MM-DD). Defaults to today.")
@click.pass_context
def nutrition(ctx: click.Context, date_str: str | None) -> None:
    """Print the nutrition log for a given date."""
    cfg = ctx.obj["cfg"]
    db_path = _resolve(cfg, "db_path")
    target_date = date_str or date.today().isoformat()

    conn = init_db(db_path)
    rows = get_nutrition_log(conn, target_date)
    conn.close()

    if not rows:
        click.echo(f"No nutrition data for {target_date}")
        return
    click.echo(json.dumps(rows, indent=2, default=str))


@cli.command("workouts")
@click.option("--days", default=7, help="Number of days to look back (default 7).")
@click.pass_context
def workouts_cmd(ctx: click.Context, days: int) -> None:
    """Print recent workout data."""
    cfg = ctx.obj["cfg"]
    db_path = _resolve(cfg, "db_path")
    end = date.today().isoformat()
    start = (date.today() - timedelta(days=days)).isoformat()

    conn = init_db(db_path)
    rows = get_workouts(conn, start, end)
    conn.close()

    if not rows:
        click.echo(f"No workout data in the last {days} days")
        return
    click.echo(json.dumps(rows, indent=2, default=str))


@cli.command("weight")
@click.option("--days", default=30, help="Number of days to look back (default 30).")
@click.pass_context
def weight_cmd(ctx: click.Context, days: int) -> None:
    """Print weight trend data."""
    cfg = ctx.obj["cfg"]
    db_path = _resolve(cfg, "db_path")

    conn = init_db(db_path)
    rows = get_weight_trend(conn, days=days)
    conn.close()

    if not rows:
        click.echo(f"No weight data in the last {days} days")
        return
    click.echo(json.dumps(rows, indent=2, default=str))


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show database statistics and the last import time."""
    cfg = ctx.obj["cfg"]
    db_path = _resolve(cfg, "db_path")

    db_file = Path(db_path)
    if not db_file.exists():
        click.echo(f"Database does not exist at {db_path}. Run 'macroclaw init' first.")
        return

    conn = init_db(db_path)

    tables = ["nutrition_log", "workouts", "weight_log", "daily_summary", "export_history"]
    click.echo(f"Database: {db_path}")
    click.echo(f"Size: {db_file.stat().st_size / 1024:.1f} KB")
    click.echo("")

    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        click.echo(f"  {table}: {count} rows")

    # Last import
    last = conn.execute(
        "SELECT export_type, file_path, rows_imported, imported_at "
        "FROM export_history ORDER BY imported_at DESC LIMIT 1"
    ).fetchone()
    click.echo("")
    if last:
        click.echo(f"Last import: {last[0]} -- {last[2]} rows at {last[3]}")
        click.echo(f"  File: {last[1]}")
    else:
        click.echo("No imports recorded yet.")

    # Macro adherence (last 7 days)
    adherence = get_macro_adherence(conn, days=7)
    if adherence.get("days_tracked", 0) > 0:
        click.echo("")
        click.echo(f"7-day macro adherence ({adherence['days_tracked']} days tracked):")
        click.echo(f"  Avg calories: {adherence.get('avg_calories', 'N/A')}")
        click.echo(f"  Calorie target: {adherence.get('avg_calorie_target', 'N/A')}")
        click.echo(f"  Adherence: {adherence.get('adherence_pct', 'N/A')}%")

    # Recent PRs
    prs = get_recent_prs(conn, days=30)
    if prs:
        click.echo("")
        click.echo("Recent PRs (last 30 days):")
        for pr in prs[:5]:
            click.echo(
                f"  {pr['exercise_name']}: {pr['max_weight_kg']} kg "
                f"x {pr['reps_at_max']} ({pr['date']})"
            )

    conn.close()


# Register automation subcommands
from automation.cli import auto_group  # noqa: E402

cli.add_command(auto_group)

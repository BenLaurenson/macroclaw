"""CLI commands for the automation module."""

import logging
import sys

import click

logger = logging.getLogger("macroclaw.automation")


@click.group("auto")
def auto_group():
    """MacroFactor UI automation commands."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )


@auto_group.command("record")
@click.argument("name")
def record(name: str):
    """Record a click sequence. Click through the export flow, then Ctrl+C to stop.

    NAME is the sequence name (e.g. "daily" or "bulk").
    """
    from automation.recorder import record_sequence

    record_sequence(name)


@auto_group.command("daily")
@click.option("--speed", default=1.0, help="Speed multiplier (0.5=fast, 2.0=slow).")
@click.option("--download-timeout", default=30.0, help="Seconds to wait for .xlsx download.")
def daily(speed: float, download_timeout: float):
    """Replay the 'daily' export sequence and ingest the result."""
    from automation.export import run_recorded_export

    result = run_recorded_export("daily", speed=speed, download_timeout=download_timeout)
    click.echo(f"Export saved: {result}")


@auto_group.command("bulk")
@click.option("--speed", default=1.0, help="Speed multiplier (0.5=fast, 2.0=slow).")
@click.option("--download-timeout", default=120.0, help="Seconds to wait for .xlsx download.")
def bulk(speed: float, download_timeout: float):
    """Replay the 'bulk' export sequence and ingest the result."""
    from automation.export import run_recorded_export

    result = run_recorded_export("bulk", speed=speed, download_timeout=download_timeout)
    click.echo(f"Export saved: {result}")


@auto_group.command("show")
@click.argument("name")
def show(name: str):
    """Show the steps in a recorded sequence."""
    from automation.recorder import edit_sequence

    edit_sequence(name)


@auto_group.command("play")
@click.argument("name")
@click.option("--speed", default=1.0, help="Speed multiplier.")
def play(name: str, speed: float):
    """Replay any recorded sequence by name (without waiting for download)."""
    from automation.recorder import replay_sequence

    replay_sequence(name, speed=speed)


# ---------------------------------------------------------------------------
# AI-driven commands (Claude Computer Use)
# ---------------------------------------------------------------------------


@auto_group.command("export-daily")
@click.option(
    "--model", default="claude-sonnet-4-5",
    help="Model to use (claude-sonnet-4-5, claude-opus-4-6, or full model ID).",
)
@click.option("--download-timeout", default=30.0, help="Seconds to wait for .xlsx download.")
def export_daily(model: str, download_timeout: float):
    """AI-driven daily export: Claude navigates MacroFactor to export last 7 days."""
    from automation.computer_use import run_export_with_agent

    result = run_export_with_agent("daily", model=model, download_timeout=download_timeout)
    click.echo(f"Export saved: {result}")


@auto_group.command("export-bulk")
@click.option(
    "--model", default="claude-sonnet-4-5",
    help="Model to use (claude-sonnet-4-5, claude-opus-4-6, or full model ID).",
)
@click.option("--download-timeout", default=120.0, help="Seconds to wait for .xlsx download.")
def export_bulk(model: str, download_timeout: float):
    """AI-driven bulk export: Claude navigates MacroFactor to export all data."""
    from automation.computer_use import run_export_with_agent

    result = run_export_with_agent("bulk", model=model, download_timeout=download_timeout)
    click.echo(f"Export saved: {result}")


@auto_group.command("run")
@click.argument("instruction")
@click.option(
    "--model", default="claude-sonnet-4-5",
    help="Model to use (claude-sonnet-4-5, claude-opus-4-6, or full model ID).",
)
@click.option("--max-iterations", default=50, help="Max API round-trips (safety cap).")
def run_agent(instruction: str, model: str, max_iterations: int):
    """Free-form AI control of MacroFactor. Pass any instruction in quotes.

    Example: macroclaw auto run "Take a screenshot and describe what you see"
    """
    from automation.computer_use import agent_loop

    result = agent_loop(instruction, model=model, max_iterations=max_iterations)
    click.echo(result)

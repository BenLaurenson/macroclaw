"""CLI commands for the automation module."""

import logging
import sys
from pathlib import Path

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


@auto_group.command("daily")
@click.option("--confidence", default=0.80, help="Image match threshold (0.0-1.0).")
@click.option("--timeout", default=30.0, help="Download timeout in seconds.")
def daily(confidence: float, timeout: float):
    """Run daily Quick Export (last 7 days, nutrition + workouts)."""
    from automation.export import run_daily_export

    result = run_daily_export(confidence=confidence, download_timeout=timeout)
    click.echo(f"Export saved: {result}")


@auto_group.command("bulk")
@click.option("--confidence", default=0.80, help="Image match threshold (0.0-1.0).")
@click.option("--timeout", default=120.0, help="Download timeout in seconds.")
def bulk(confidence: float, timeout: float):
    """Run bulk Granular Export (all data, all time)."""
    from automation.export import run_bulk_export

    result = run_bulk_export(confidence=confidence, download_timeout=timeout)
    click.echo(f"Export saved: {result}")


@auto_group.command("capture")
@click.argument("name")
def capture(name: str):
    """Capture a reference screenshot interactively.

    Takes a screenshot, then opens Preview so you can crop the region
    you need and save it to the images/ directory.

    NAME is the filename to save (e.g. "more_tab.png").
    """
    import subprocess
    import time

    from automation.vision import IMAGE_DIR

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    dest = IMAGE_DIR / name
    if not dest.suffix:
        dest = dest.with_suffix(".png")

    click.echo("You have 3 seconds to position the MacroFactor window...")
    for i in range(3, 0, -1):
        click.echo(f"  {i}...")
        time.sleep(1)

    # Use macOS screencapture in interactive mode (crosshair selection)
    click.echo("Select the region to capture (drag to select)...")
    subprocess.run(["screencapture", "-i", str(dest)], check=True)

    if dest.exists():
        click.echo(f"Saved: {dest}")
    else:
        click.echo("Capture cancelled.")


@auto_group.command("test")
@click.argument("name")
@click.option("--confidence", default=0.80, help="Match threshold.")
def test_image(name: str, confidence: float):
    """Test if a reference image can be found on screen right now."""
    from automation.vision import find_on_screen

    pos = find_on_screen(name, confidence=confidence)
    if pos:
        click.echo(f"Found '{name}' at ({pos[0]}, {pos[1]})")
    else:
        click.echo(f"'{name}' NOT found on screen (threshold={confidence})")

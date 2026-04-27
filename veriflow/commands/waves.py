from pathlib import Path

from veriflow.core import VeriFlowError
from veriflow.core.csv_store import get_tile_row
from veriflow.core.validator import validate_database
from veriflow.ui.output import console, print_wave_url, print_done


def cmd_waves(db: Path, tile_number: str, run_id: str | None = None) -> None:
    """Open waveform viewer for a specific run of a tile."""

    validate_database(db)
    tile_number_str = f"{int(tile_number):04d}"

    # Look up tile_id
    tile_row = get_tile_row(db / "tile_index.csv", tile_number_str)
    tile_id = tile_row["tile_id"]
    tile_dir = db / "tiles" / tile_id
    runs_dir = tile_dir / "runs"

    # Resolve run_id — use specified or find latest
    if run_id:
        target_run = runs_dir / run_id
        if not target_run.exists():
            raise VeriFlowError(f"Run not found: {target_run}")
    else:
        import re
        pattern = re.compile(r"^run-(\d{3})$")
        runs = sorted(
            [d for d in runs_dir.iterdir() if d.is_dir() and pattern.match(d.name)],
            key=lambda d: int(pattern.match(d.name).group(1)),
        )
        if not runs:
            raise VeriFlowError(f"No runs found for tile {tile_number_str}")
        target_run = runs[-1]

    wave_path = target_run / "out" / "sim" / "waves" / "waves.vcd"

    if not wave_path.exists():
        raise VeriFlowError(
            f"No waveform file found for {target_run.name}\n"
            f"  Expected: {wave_path}\n"
            f"  Make sure the run included simulation (not --skip-sim)."
        )

    console.print()
    console.print(f"  [secondary]tile[/secondary]  [id]{tile_id}[/id]")
    console.print(f"  [secondary]run [/secondary]  [id]{target_run.name}[/id]")

    import os

    if os.environ.get("SEMICOLAB_DOCKER"):
        from veriflow.core.sim_runner import open_surfer
        open_surfer(wave_path)
    else:
        from veriflow.core.sim_runner import launch_gtkwave
        launch_gtkwave(wave_path)
        print_done("GTKWave launched.")

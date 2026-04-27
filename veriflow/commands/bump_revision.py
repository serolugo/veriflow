import shutil
from datetime import date
from pathlib import Path

from veriflow.core import VeriFlowError
from veriflow.core.csv_store import get_tile_row, update_tile_index
from veriflow.core.tile_id import generate_tile_id, parse_tile_id
from veriflow.core.validator import validate_database
from veriflow.ui.output import console, print_section, print_done


def cmd_bump_revision(db: Path, tile_number: str) -> None:
    validate_database(db)
    tile_number_str = f"{int(tile_number):04d}"
    tile_index_path = db / "tile_index.csv"

    tile_row = get_tile_row(tile_index_path, tile_number_str)
    old_tile_id = tile_row["tile_id"]

    parsed = parse_tile_id(old_tile_id)
    new_revision = parsed["id_revision"] + 1
    new_version = 1

    new_tile_id = generate_tile_id(
        parsed["id_prefix"],
        parsed["tile_number"],
        new_version,
        new_revision,
        today=date.today(),
    )

    print_section("Bump revision")
    console.print(f"  [secondary]old[/secondary]  [id]{old_tile_id}[/id]  [secondary](preserved)[/secondary]")
    console.print(f"  [secondary]new[/secondary]  [id]{new_tile_id}[/id]")
    console.print()

    old_dir = db / "tiles" / old_tile_id
    new_dir = db / "tiles" / new_tile_id
    if not old_dir.exists():
        raise VeriFlowError(f"Tile directory not found: {old_dir}")
    if new_dir.exists():
        raise VeriFlowError(f"New tile directory already exists: {new_dir}")

    new_dir.mkdir(parents=True)

    old_works = old_dir / "works"
    new_works = new_dir / "works"
    if old_works.exists():
        shutil.copytree(old_works, new_works)
    else:
        for sub in ("works/rtl", "works/tb"):
            d = new_dir / sub
            d.mkdir(parents=True, exist_ok=True)
            (d / ".gitkeep").touch()

    old_readme = old_dir / "README.md"
    if old_readme.exists():
        shutil.copy2(old_readme, new_dir / "README.md")

    runs_dir = new_dir / "runs"
    runs_dir.mkdir()
    (runs_dir / ".gitkeep").touch()

    updated_row = {
        "tile_number": tile_number_str,
        "tile_id": new_tile_id,
        "tile_name": tile_row["tile_name"],
        "tile_author": tile_row["tile_author"],
        "semicolab": tile_row.get("semicolab", "true"),
        "version": f"{new_version:02d}",
        "revision": f"{new_revision:02d}",
    }
    update_tile_index(tile_index_path, tile_number_str, updated_row)

    print_done(
        f"Revision bumped  ·  "
        f"[secondary]r{parsed['id_revision']:02d}[/secondary] → [id]r{new_revision:02d}[/id]  ·  "
        f"version reset to [id]v{new_version:02d}[/id]"
    )

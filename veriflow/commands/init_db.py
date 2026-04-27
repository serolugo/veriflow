from pathlib import Path

from veriflow.core import VeriFlowError
from veriflow.ui.output import console, print_section, print_done


_PROJECT_CONFIG_TEMPLATE = """\
id_prefix: ""
project_name: ""
repo: ""
semicolab: true
description: |
  
"""

_TILE_INDEX_HEADER = "tile_number,tile_id,tile_name,tile_author,version,revision\n"
_RECORDS_HEADER = (
    "Tile_ID,Run_ID,Date,Author,Objective,Status,"
    "Version,Revision,Connectivity,Simulation,Synthesis,"
    "Tool_Version,Main_Change,Run_Path,Tags\n"
)


def cmd_init(db: Path, force: bool = False) -> None:
    """Initialize a new VeriFlow database at the given path."""

    if db.exists() and not force:
        raise VeriFlowError(
            f"Database directory already exists: {db}\n"
            f"  Use --force to overwrite."
        )

    print_section("Initializing database")
    console.print(f"  [secondary]path[/secondary]  [id]{db.resolve()}[/id]\n")

    # 1. Create root
    db.mkdir(parents=True, exist_ok=True)

    # 2. Create tiles/
    tiles_dir = db / "tiles"
    tiles_dir.mkdir(exist_ok=True)
    (tiles_dir / ".gitkeep").touch()

    # 3. Create config/
    config_dir = db / "config"
    config_dir.mkdir(exist_ok=True)

    # 4. Write project_config.yaml template
    project_cfg = db / "project_config.yaml"
    project_cfg.write_text(_PROJECT_CONFIG_TEMPLATE, encoding="utf-8")

    # 5. Create tile_index.csv (empty)
    tile_index = db / "tile_index.csv"
    tile_index.write_text("", encoding="utf-8")

    # 6. Create records.csv (empty)
    records = db / "records.csv"
    records.write_text("", encoding="utf-8")

    # Show structure
    console.print(f"  [secondary]  {db}/[/secondary]")
    console.print(f"  [secondary]  ├── project_config.yaml  ← fill this next[/secondary]")
    console.print(f"  [secondary]  ├── tile_index.csv[/secondary]")
    console.print(f"  [secondary]  ├── records.csv[/secondary]")
    console.print(f"  [secondary]  ├── config/[/secondary]")
    console.print(f"  [secondary]  └── tiles/[/secondary]")
    console.print()

    print_done(
        f"Database ready  ·  fill [id]{db / 'project_config.yaml'}[/id] to continue"
    )

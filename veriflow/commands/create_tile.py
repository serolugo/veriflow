from datetime import date
from pathlib import Path

import yaml

from veriflow.core import VeriFlowError
from veriflow.core.csv_store import append_tile_index, get_next_tile_number
from veriflow.core.tile_id import generate_tile_id
from veriflow.core.validator import validate_database, validate_project_config
from veriflow.generators.readme import generate_readme
from veriflow.models.project_config import ProjectConfig
from veriflow.models.tile_config import TileConfig


_TILE_CONFIG_TEMPLATE = """\
tile_name: ""
tile_author: ""
top_module: ""

description: |
  
ports: |
  
usage_guide: |
  
tb_description: |
  
"""

_RUN_CONFIG_TEMPLATE = """\
run_author: ""
objective: ""
tags: ""

main_change: |
  
notes: |
  
"""


def cmd_create_tile(db: Path) -> None:
    """Create a new tile entry in the database."""

    validate_database(db)

    # 1. Read id_prefix
    project_cfg_path = db / "project_config.yaml"
    raw = yaml.safe_load(project_cfg_path.read_text(encoding="utf-8")) or {}
    project_config = ProjectConfig.from_dict(raw)
    validate_project_config(project_config)

    # 2. Get next tile_number
    tile_index_path = db / "tile_index.csv"
    tile_number = get_next_tile_number(tile_index_path)
    tile_number_str = f"{tile_number:04d}"

    # 3. Set version/revision
    id_version = 1
    id_revision = 1

    # 4. Generate tile_id
    tile_id = generate_tile_id(
        project_config.id_prefix,
        tile_number,
        id_version,
        id_revision,
        today=date.today(),
    )

    print(f"[create-tile] Generating tile {tile_number_str} → {tile_id}")

    # 5. Create config/tile_XXXX/
    config_tile_dir = db / "config" / f"tile_{tile_number_str}"
    config_tile_dir.mkdir(parents=True, exist_ok=True)
    print(f"[create-tile] Created {config_tile_dir.relative_to(db)}")

    # 6. Write tile_config.yaml
    (config_tile_dir / "tile_config.yaml").write_text(_TILE_CONFIG_TEMPLATE, encoding="utf-8")
    print(f"[create-tile] Written tile_config.yaml")

    # 7. Write run_config.yaml
    (config_tile_dir / "run_config.yaml").write_text(_RUN_CONFIG_TEMPLATE, encoding="utf-8")
    print(f"[create-tile] Written run_config.yaml")

    # 8. Create src/rtl/ and src/tb/ with .gitkeep + tb template
    import shutil
    template_dir = Path(__file__).parent.parent / "template"
    for sub in ("src/rtl", "src/tb"):
        d = config_tile_dir / sub
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").touch()
    # Copy user-facing tb template into src/tb/
    tb_template = template_dir / "tb_tile_template.v"
    if tb_template.exists():
        shutil.copy2(tb_template, config_tile_dir / "src" / "tb" / "tb_tile.v")
    print(f"[create-tile] Created src/rtl/ and src/tb/ (with tb_tile.v template)")

    # 9. Create tiles/<tile_id>/
    tile_dir = db / "tiles" / tile_id
    tile_dir.mkdir(parents=True, exist_ok=True)
    print(f"[create-tile] Created tiles/{tile_id}/")

    # 10. Generate README.md with empty fields
    empty_tile_config = TileConfig.from_dict({})
    generate_readme(tile_id, empty_tile_config, tile_dir / "README.md")
    print(f"[create-tile] Generated README.md")

    # 11. Create works/rtl/ and works/tb/ with .gitkeep
    for sub in ("works/rtl", "works/tb"):
        d = tile_dir / sub
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").touch()
    print(f"[create-tile] Created works/")

    # 12. Create runs/ with .gitkeep
    runs_dir = tile_dir / "runs"
    runs_dir.mkdir(exist_ok=True)
    (runs_dir / ".gitkeep").touch()
    print(f"[create-tile] Created runs/")

    # 13. Append row to tile_index.csv
    append_tile_index(tile_index_path, {
        "tile_number": tile_number_str,
        "tile_id": tile_id,
        "tile_name": "",
        "tile_author": "",
        "version": f"{id_version:02d}",
        "revision": f"{id_revision:02d}",
    })
    print(f"[create-tile] Appended row to tile_index.csv")

    print()
    print("✓ Tile created successfully.")
    print(f"  Tile Number : {tile_number_str}")
    print(f"  Tile ID     : {tile_id}")
    print(f"  Config      : {config_tile_dir.relative_to(db)}")
    print(f"  Next        : Fill in config/tile_{tile_number_str}/tile_config.yaml")
    print(f"                Add RTL to config/tile_{tile_number_str}/src/rtl/")

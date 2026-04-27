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
from veriflow.ui.output import console, print_done, print_section


_TILE_CONFIG_TEMPLATE = """\
# =============================================================================
# TILE INFORMATION  (permanent -- fill once)
# =============================================================================

tile_name: ""       # Display name for this tile
tile_author: ""     # Your full name
top_module: ""      # Must match the RTL filename exactly (e.g. adder_tile)

description: |
  # What does this tile do?

ports: |
  # Describe how your tile uses the SemiCoLab port convention:
  #   clk / arst_n     - clock and reset
  #   csr_in[15:0]     - control inputs
  #   data_reg_a / b   - input data (32-bit)
  #   data_reg_c       - output data (32-bit)
  #   csr_out[15:0]    - status outputs

usage_guide: |
  # How should this tile be used?

tb_description: |
  # Briefly describe your testbench approach

# =============================================================================
# RUN INFORMATION  (update before each run)
# =============================================================================

run_author: ""      # Who is running this verification
objective: ""       # What are you trying to verify in this run
tags: ""            # Comma-separated tags (e.g. initial, fix, refactor)

main_change: |
  # What changed since the last run?

notes: |
  # Any additional notes for this run
"""


def cmd_create_tile(db: Path) -> None:
    """Create a new tile entry in the database."""

    validate_database(db)

    # 1. Read project config
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

    print_section("Creating tile")
    console.print(f"  [secondary]tile number[/secondary]  [id]{tile_number_str}[/id]")
    console.print(f"  [secondary]tile id    [/secondary]  [id]{tile_id}[/id]")
    console.print()

    # 5. Create config/tile_XXXX/
    config_tile_dir = db / "config" / f"tile_{tile_number_str}"
    config_tile_dir.mkdir(parents=True, exist_ok=True)

    # 6. Write single tile_config.yaml (tile + run fields merged)
    (config_tile_dir / "tile_config.yaml").write_text(_TILE_CONFIG_TEMPLATE, encoding="utf-8")

    # 7. Create src/rtl/ and src/tb/ with templates
    import shutil
    template_dir = Path(__file__).parent.parent / "template"
    for sub in ("src/rtl", "src/tb"):
        d = config_tile_dir / sub
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").touch()

    tb_dir = config_tile_dir / "src" / "tb"
    if project_config.semicolab:
        tb_base = template_dir / "tb_base.v"
        tb_tasks = template_dir / "tb_tasks.v"
        if tb_base.exists():
            shutil.copy2(tb_base, tb_dir / "tb_tile.v")
        if tb_tasks.exists():
            shutil.copy2(tb_tasks, tb_dir / "tb_tasks.v")
    else:
        tb_universal = template_dir / "tb_universal_template.v"
        if tb_universal.exists():
            shutil.copy2(tb_universal, tb_dir / "tb_tile.v")

    # 8. Create tiles/<tile_id>/
    tile_dir = db / "tiles" / tile_id
    tile_dir.mkdir(parents=True, exist_ok=True)

    # 9. Generate README.md with empty fields
    empty_tile_config = TileConfig.from_dict({})
    generate_readme(tile_id, empty_tile_config, tile_dir / "README.md")

    # 10. Create works/ and runs/
    for sub in ("works/rtl", "works/tb"):
        d = tile_dir / sub
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").touch()

    runs_dir = tile_dir / "runs"
    runs_dir.mkdir(exist_ok=True)
    (runs_dir / ".gitkeep").touch()

    # 11. Append row to tile_index.csv
    append_tile_index(tile_index_path, {
        "tile_number": tile_number_str,
        "tile_id": tile_id,
        "tile_name": "",
        "tile_author": "",
        "version": f"{id_version:02d}",
        "revision": f"{id_revision:02d}",
        "semicolab": "true" if project_config.semicolab else "false",
    })

    # 12. Show generated structure
    mode = "semicolab" if project_config.semicolab else "universal"
    console.print(f"  [secondary]  config/tile_{tile_number_str}/[/secondary]")
    console.print(f"  [secondary]  ├── tile_config.yaml[/secondary]")
    console.print(f"  [secondary]  └── src/[/secondary]")
    console.print(f"  [secondary]      ├── rtl/   ← add your RTL here[/secondary]")
    console.print(f"  [secondary]      └── tb/    ({mode} testbench)[/secondary]")
    console.print()

    print_done(
        f"Tile [id]{tile_number_str}[/id] created  ·  "
        f"fill [id]config/tile_{tile_number_str}/tile_config.yaml[/id] to continue"
    )

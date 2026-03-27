from pathlib import Path

from veriflow.models.tile_config import TileConfig


def generate_readme(
    tile_id: str,
    tile_config: TileConfig,
    output_path: Path,
) -> None:
    content = f"""# Tile ID : "{tile_id}"

## Title: "{tile_config.tile_name}"

## Top module: "{tile_config.top_module}"

## Description:
"{tile_config.description}"

## Port convention:
"{tile_config.ports}"

## Usage guide:
"{tile_config.usage_guide}"

## Testbench description:
"{tile_config.tb_description}"
"""
    output_path.write_text(content, encoding="utf-8")

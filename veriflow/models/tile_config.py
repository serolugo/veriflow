from dataclasses import dataclass


@dataclass
class TileConfig:
    # ── Tile (permanent) ──────────────────────────────────────────────────────
    tile_name: str
    tile_author: str
    top_module: str
    description: str
    ports: str
    usage_guide: str
    tb_description: str
    # ── Run (updated each run) ────────────────────────────────────────────────
    run_author: str
    objective: str
    tags: str
    main_change: str
    notes: str

    @classmethod
    def from_dict(cls, data: dict) -> "TileConfig":
        return cls(
            tile_name=data.get("tile_name", "") or "",
            tile_author=data.get("tile_author", "") or "",
            top_module=data.get("top_module", "") or "",
            description=data.get("description", "") or "",
            ports=data.get("ports", "") or "",
            usage_guide=data.get("usage_guide", "") or "",
            tb_description=data.get("tb_description", "") or "",
            run_author=data.get("run_author", "") or "",
            objective=data.get("objective", "") or "",
            tags=data.get("tags", "") or "",
            main_change=data.get("main_change", "") or "",
            notes=data.get("notes", "") or "",
        )

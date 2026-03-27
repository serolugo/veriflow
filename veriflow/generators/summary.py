from pathlib import Path


def generate_summary(
    tile_id: str,
    tile_name: str,
    run_id: str,
    date: str,
    connectivity: str,
    simulation: str,
    synthesis: str,
    cells: str,
    warnings: str,
    errors: str,
    sim_time: str,
    precheck_status: str,
    output_path: Path,
) -> str:
    cells_str  = f"{cells} cells" if cells else "-"
    sim_str    = f"{sim_time}" if sim_time else "-"

    content = f"""# Run Summary

**Tile ID:** {tile_id}
**Tile:**    {tile_name}
**Run:**     {run_id}
**Date:**    {date}

---

| Stage        | Result        | Details          |
|--------------|---------------|------------------|
| Connectivity | {connectivity:<13} |                  |
| Simulation   | {simulation:<13} | {sim_str:<16} |
| Synthesis    | {synthesis:<13} | {cells_str:<16} |

---

**Warnings:** {warnings}
**Errors:**   {errors}

---

## Precheck: {precheck_status}
"""
    output_path.write_text(content, encoding="utf-8")
    return content

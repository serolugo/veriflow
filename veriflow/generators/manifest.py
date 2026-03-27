from pathlib import Path


def _render_manifest(data: dict) -> str:
    """
    Custom YAML serializer for manifest.yaml.
    Produces readable YAML with blank lines between logical sections.
    Does NOT use yaml.dump.
    """

    def val(v) -> str:
        if v is None:
            return '""'
        if isinstance(v, list):
            if not v:
                return "[]"
            items = "\n".join(f'  - "{item}"' for item in v)
            return f"\n{items}"
        s = str(v)
        if not s:
            return '""'
        return f'"{s}"'

    def pair(key: str, value, indent: int = 0) -> str:
        prefix = "  " * indent
        return f"{prefix}{key}: {val(value)}"

    lines = []

    # Section 1: identity
    lines.append(pair("tile_id", data.get("tile_id", "")))
    lines.append(pair("run_id", data.get("run_id", "")))
    lines.append(pair("date", data.get("date", "")))
    lines.append(pair("author", data.get("author", "")))
    lines.append("")

    # Section 2: run objective / status
    lines.append(pair("objective", data.get("objective", "")))
    lines.append(pair("status", data.get("status", "")))
    lines.append("")

    # Section 3: tile info
    lines.append("tile:")
    tile = data.get("tile", {})
    lines.append(pair("tile_name", tile.get("tile_name", ""), indent=1))
    lines.append(pair("top_module", tile.get("top_module", ""), indent=1))
    lines.append(pair("version", tile.get("version", ""), indent=1))
    lines.append(pair("revision", tile.get("revision", ""), indent=1))
    lines.append("")

    # Section 4: tools
    lines.append("tools:")
    tools = data.get("tools", {})
    lines.append(pair("simulator", tools.get("simulator", "iverilog"), indent=1))
    lines.append(pair("simulator_version", tools.get("simulator_version", ""), indent=1))
    lines.append(pair("synthesizer", tools.get("synthesizer", "yosys"), indent=1))
    lines.append(pair("synthesizer_version", tools.get("synthesizer_version", ""), indent=1))
    lines.append("")

    # Section 5: run params
    lines.append("run:")
    run = data.get("run", {})
    lines.append(pair("sim_time", run.get("sim_time", ""), indent=1))
    lines.append(pair("seed", run.get("seed", ""), indent=1))
    lines.append("")

    # Section 6: sources
    lines.append("sources:")
    sources = data.get("sources", {})
    lines.append(pair("rtl", sources.get("rtl", []), indent=1))
    lines.append(pair("tb", sources.get("tb", []), indent=1))
    lines.append("")

    # Section 7: artifacts
    lines.append("artifacts:")
    artifacts = data.get("artifacts", {})
    lines.append(pair("connectivity_log", artifacts.get("connectivity_log", []), indent=1))
    lines.append(pair("sim_log", artifacts.get("sim_log", []), indent=1))
    lines.append(pair("synth_log", artifacts.get("synth_log", []), indent=1))
    lines.append(pair("wave", artifacts.get("wave", []), indent=1))
    lines.append("")

    # Section 8: results
    lines.append("results:")
    results = data.get("results", {})
    lines.append(pair("connectivity", results.get("connectivity", ""), indent=1))
    lines.append(pair("simulation", results.get("simulation", ""), indent=1))
    lines.append(pair("synthesis", results.get("synthesis", ""), indent=1))
    lines.append(pair("cells", results.get("cells", ""), indent=1))
    lines.append(pair("warnings", results.get("warnings", ""), indent=1))
    lines.append(pair("errors", results.get("errors", ""), indent=1))

    return "\n".join(lines) + "\n"


def generate_manifest(data: dict, output_path: Path) -> None:
    output_path.write_text(_render_manifest(data), encoding="utf-8")

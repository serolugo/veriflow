"""
veriflow.ui.tui
---------------
Interactive navigator: database → tile → action.
Uses questionary for arrow-key selection.
Remembers last context in ~/.semicolab_last so the user can
repeat the previous run with a single Enter.
"""

import json
import sys
from pathlib import Path

from rich.console import Console
from veriflow.ui.theme import VERIFLOW_THEME, BLUE, GREEN, ORANGE, GREY, WHITE

console = Console(theme=VERIFLOW_THEME)

LAST_FILE = Path.home() / ".semicolab_last"


# ── Persistence ────────────────────────────────────────────────────────────────

def _load_last() -> dict:
    try:
        return json.loads(LAST_FILE.read_text())
    except Exception:
        return {}


def _save_last(data: dict) -> None:
    try:
        LAST_FILE.write_text(json.dumps(data))
    except Exception:
        pass


# ── Database discovery ─────────────────────────────────────────────────────────

def _find_databases(root: Path) -> list[Path]:
    """
    Find VeriFlow databases by locating project_config.yaml.
    Searches root itself and one level of subdirectories.
    """
    hits = []
    candidates = [root] + sorted(root.iterdir()) if root.is_dir() else []
    for p in candidates:
        if p.is_dir() and (p / "project_config.yaml").exists():
            hits.append(p)
    return hits


def _list_tiles(db: Path) -> list[dict]:
    """Return tile info from tile_index.csv."""
    index = db / "tile_index.csv"
    tiles = []
    if not index.exists():
        return tiles
    import csv
    with open(index, newline="") as f:
        for row in csv.DictReader(f):
            tiles.append(row)
    return tiles


def _list_runs(db: Path, tile_number: str) -> list[str]:
    """Return sorted run IDs for a tile (newest first)."""
    runs_dir = db / "tiles" / tile_number / "runs"
    if not runs_dir.exists():
        return []
    runs = sorted(
        [d.name for d in runs_dir.iterdir() if d.is_dir() and d.name.startswith("run-")],
        reverse=True,
    )
    return runs


# ── questionary helpers ────────────────────────────────────────────────────────

def _q_select(message: str, choices: list, instruction: str = "") -> str | None:
    try:
        import questionary
        from questionary import Style as QStyle

        q_style = QStyle([
            ("qmark",        f"fg:{ORANGE} bold"),
            ("question",     f"fg:{WHITE} bold"),
            ("answer",       f"fg:{GREEN} bold"),
            ("pointer",      f"fg:{ORANGE} bold"),
            ("highlighted",  f"fg:{ORANGE} bold"),
            ("selected",     f"fg:{GREEN}"),
            ("instruction",  f"fg:{GREY}"),
            ("text",         f"fg:{WHITE}"),
        ])

        return questionary.select(
            message,
            choices=choices,
            instruction=instruction or "(↑↓ navigate, Enter select)",
            style=q_style,
        ).ask()

    except ImportError:
        # Fallback: numbered list
        console.print(f"\n  [label]{message}[/label]")
        for i, c in enumerate(choices, 1):
            label = c if isinstance(c, str) else c.title
            console.print(f"  [secondary]{i}.[/secondary] {label}")
        try:
            idx = int(input("\n  > ")) - 1
            return choices[idx] if isinstance(choices[idx], str) else choices[idx].value
        except (ValueError, IndexError):
            return None


# ── Main TUI flow ──────────────────────────────────────────────────────────────

def run_tui(workspace: Path = Path(".")) -> None:
    """
    Full interactive flow:
    1. Offer to repeat last run (if any)
    2. Select database → tile → action
    3. Execute selected action via CLI
    """
    import subprocess

    last = _load_last()

    # ── Offer repeat ──────────────────────────────────────────────────────────
    if last.get("db") and last.get("tile") and last.get("action"):
        console.print(
            f"  [secondary]Last:[/secondary]  "
            f"[id]{last['db']}[/id]  ·  "
            f"[id]{last['tile']}[/id]  ·  "
            f"[secondary]{last['action']}[/secondary]"
        )
        console.print()

        repeat = _q_select(
            "Repeat last run?",
            choices=["Yes — repeat", "No — navigate"],
        )
        if repeat is None or repeat == "Yes — repeat":
            _execute(last, workspace)
            return
        console.print()

    # ── Select database ───────────────────────────────────────────────────────
    databases = _find_databases(workspace)

    if not databases:
        console.print("  [warn]⚠[/warn]  No VeriFlow databases found in current directory.")
        console.print(f"  [secondary]Run [label]veriflow --db <path> init[/label] to create one.[/secondary]")
        console.print()
        return

    db_choices = [str(d) for d in databases]
    db_str = _q_select("Select database:", db_choices)
    if db_str is None:
        return
    db = Path(db_str)
    console.print()

    # ── Select tile ───────────────────────────────────────────────────────────
    tiles = _list_tiles(db)

    if not tiles:
        console.print("  [warn]⚠[/warn]  No tiles found. Create one with [label]create-tile[/label].")
        _save_last({"db": str(db), "tile": None, "action": "create-tile"})
        _execute({"db": str(db), "tile": None, "action": "create-tile"}, workspace)
        return

    tile_choices = [
        f"{t.get('tile_number', '?')}  {t.get('tile_name', '')}  "
        f"[secondary]v{t.get('version', '?')}r{t.get('revision', '?')}[/secondary]"
        for t in tiles
    ]
    tile_choices.append("── New tile")

    tile_str = _q_select("Select tile:", tile_choices)
    if tile_str is None:
        return

    if "New tile" in tile_str:
        ctx = {"db": str(db), "tile": None, "action": "create-tile"}
        _save_last(ctx)
        _execute(ctx, workspace)
        return

    tile_idx = tile_choices.index(tile_str)
    tile_number = tiles[tile_idx].get("tile_number", "")
    console.print()

    # ── Select action ─────────────────────────────────────────────────────────
    runs = _list_runs(db, tile_number)
    action_choices = ["New run"]
    for r in runs:
        action_choices.append(f"Open {r}")
    action_choices += ["bump-version", "bump-revision"]

    action_str = _q_select("Select action:", action_choices)
    if action_str is None:
        return
    console.print()

    ctx = {"db": str(db), "tile": tile_number, "action": action_str}
    _save_last(ctx)
    _execute(ctx, workspace)


# ── Execute ────────────────────────────────────────────────────────────────────

def _execute(ctx: dict, workspace: Path) -> None:
    import subprocess

    db      = ctx["db"]
    tile    = ctx.get("tile")
    action  = ctx.get("action", "")

    cmd: list[str] = ["veriflow", "--db", db]

    if action == "New run":
        cmd += ["run", "--tile", tile]
    elif action.startswith("Open run-"):
        run_id = action.split("Open ")[-1]
        cmd += ["waves", "--tile", tile, "--run", run_id]
    elif action == "create-tile":
        cmd += ["create-tile"]
    elif action == "bump-version":
        cmd += ["bump-version", "--tile", tile]
    elif action == "bump-revision":
        cmd += ["bump-revision", "--tile", tile]
    else:
        console.print(f"  [warn]⚠[/warn]  Unknown action: {action}")
        return

    console.print(f"  [secondary]Running:[/secondary] [id]{' '.join(cmd)}[/id]\n")
    subprocess.run(cmd)

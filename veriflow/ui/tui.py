"""
veriflow.ui.tui
---------------
Textual TUI for VeriFlow: database → tile → runs navigator.
Replaces the questionary-based implementation.
"""

from __future__ import annotations

import csv
import os
import subprocess
from pathlib import Path

import yaml
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Tree,
)



# ─── Data helpers ──────────────────────────────────────────────────────────────

def _find_databases(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    hits: list[Path] = []
    candidates = [root] + sorted(root.iterdir())
    for p in candidates:
        if p.is_dir() and (p / "project_config.yaml").exists():
            hits.append(p)
    return hits


def _list_tiles(db: Path) -> list[dict]:
    index = db / "tile_index.csv"
    if not index.exists():
        return []
    with open(index, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _list_runs(db: Path, tile_id: str) -> list[Path]:
    """Return sorted run dirs (newest first). Uses tile_id as directory name."""
    runs_dir = db / "tiles" / tile_id / "runs"
    if not runs_dir.exists():
        return []
    return sorted(
        [d for d in runs_dir.iterdir() if d.is_dir() and d.name.startswith("run-")],
        key=lambda d: d.name,
        reverse=True,
    )


def _run_manifest(run_dir: Path) -> dict:
    manifest = run_dir / "manifest.yaml"
    if not manifest.exists():
        return {}
    try:
        return yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _status_icon(status: str) -> str:
    return {"PASS": "✅", "FAIL": "❌", "PARTIAL": "⚠ "}.get(status, " · ")


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def _tile_config_path(db: Path, tile_number: str) -> Path:
    padded = f"{int(tile_number):04d}"
    return db / "config" / f"tile_{padded}" / "tile_config.yaml"


# ─── CSS ───────────────────────────────────────────────────────────────────────

APP_CSS = """
Screen {
    background: #1a1a2e;
}

#breadcrumb {
    height: 1;
    background: #0f3460;
    color: #7EB8D4;
    padding: 0 2;
    text-style: bold;
}

#main-area {
    height: 1fr;
}

#nav-panel {
    width: 30;
    background: #16213e;
    border-right: solid #333355;
}

#nav-title {
    height: 1;
    background: #0f3460;
    color: #7EB8D4;
    padding: 0 1;
    text-style: bold;
}

Tree {
    background: #16213e;
    scrollbar-background: #16213e;
    scrollbar-corner-color: #16213e;
    color: #E8E8E8;
}

Tree > .tree--cursor {
    background: #D4956A;
    color: #1a1a2e;
    text-style: bold;
}

Tree > .tree--highlight {
    background: #D4956A 20%;
}

Tree > .tree--guides {
    color: #333355;
}

#detail-panel {
    background: #1a1a2e;
    padding: 1 2;
}

#detail-empty {
    color: #888888;
}

#tile-info {
    display: none;
}

#tile-info.visible {
    display: block;
}

#detail-title {
    color: #7EB8D4;
    text-style: bold;
}

#detail-subtitle {
    color: #888888;
}

#detail-version {
    color: #888888;
    margin-bottom: 1;
}

#runs-header {
    color: #E8E8E8;
    text-style: bold;
    margin-top: 1;
}

#runs-empty {
    color: #888888;
    display: none;
}

#runs-empty.visible {
    display: block;
}

#runs-list {
    height: auto;
    max-height: 12;
    background: #16213e;
    border: solid #333355;
    margin-top: 1;
    display: none;
}

#runs-list.visible {
    display: block;
}

ListView > ListItem {
    padding: 0 1;
    color: #E8E8E8;
}

ListView > ListItem.--highlight {
    background: #D4956A 30%;
    color: #E8E8E8;
}

#workspace-label {
    color: #888888;
    margin-top: 1;
}

Footer {
    background: #0f3460;
}
"""

FORM_CSS = """
Screen {
    background: #1a1a2e;
    padding: 0;
}

#form-scroll {
    padding: 2 4;
}

#form-title {
    color: #D4956A;
    text-style: bold;
    margin-bottom: 1;
}

.field-label {
    color: #888888;
    height: 1;
}

Input {
    margin-bottom: 1;
    background: #16213e;
    border: solid #333355;
    color: #E8E8E8;
}

Input:focus {
    border: solid #D4956A;
}

#btn-row {
    margin-top: 1;
    height: 3;
    layout: horizontal;
}

Button {
    margin-right: 2;
}

#btn-save {
    background: #D4956A;
    color: #1a1a2e;
}

#btn-cancel {
    background: #333355;
    color: #E8E8E8;
}
"""


# ─── Edit Tile Config Screen ───────────────────────────────────────────────────

TILE_CONFIG_FIELDS: list[tuple[str, str]] = [
    ("tile_name",      "Tile Name"),
    ("tile_author",    "Author"),
    ("top_module",     "Top Module"),
    ("description",    "Description"),
    ("ports",          "Ports"),
    ("usage_guide",    "Usage Guide"),
    ("tb_description", "TB Description"),
    ("run_author",     "Run Author"),
    ("objective",      "Objective"),
    ("tags",           "Tags"),
    ("main_change",    "Main Change"),
    ("notes",          "Notes"),
]


class EditTileScreen(Screen):
    CSS = FORM_CSS
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, config_path: Path, initial: dict) -> None:
        super().__init__()
        self._config_path = config_path
        self._initial = initial

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="form-scroll"):
            yield Label("Edit Tile Config", id="form-title")
            for key, label in TILE_CONFIG_FIELDS:
                yield Label(label, classes="field-label")
                yield Input(value=str(self._initial.get(key, "") or ""), id=f"f-{key}")
            with Horizontal(id="btn-row"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self._save()
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)

    def _save(self) -> None:
        data = dict(self._initial)
        for key, _ in TILE_CONFIG_FIELDS:
            data[key] = self.query_one(f"#f-{key}", Input).value
        _write_yaml(self._config_path, data)
        self.dismiss(True)


# ─── Edit Project Config Screen ────────────────────────────────────────────────

PROJECT_CONFIG_FIELDS: list[tuple[str, str]] = [
    ("id_prefix",    "ID Prefix"),
    ("project_name", "Project Name"),
    ("repo",         "Repository"),
    ("description",  "Description"),
]


class EditProjectScreen(Screen):
    CSS = FORM_CSS
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, config_path: Path, initial: dict) -> None:
        super().__init__()
        self._config_path = config_path
        self._initial = initial

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="form-scroll"):
            yield Label("Edit Project Config", id="form-title")
            for key, label in PROJECT_CONFIG_FIELDS:
                yield Label(label, classes="field-label")
                yield Input(value=str(self._initial.get(key, "") or ""), id=f"f-{key}")
            with Horizontal(id="btn-row"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self._save()
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)

    def _save(self) -> None:
        data = dict(self._initial)
        for key, _ in PROJECT_CONFIG_FIELDS:
            data[key] = self.query_one(f"#f-{key}", Input).value
        _write_yaml(self._config_path, data)
        self.dismiss(True)


# ─── Help Screen ───────────────────────────────────────────────────────────────

class HelpScreen(Screen):
    CSS = """
    Screen {
        background: #1a1a2e;
        padding: 2 4;
    }
    #help-title {
        color: #D4956A;
        text-style: bold;
        margin-bottom: 1;
    }
    Label {
        color: #E8E8E8;
    }
    """
    BINDINGS = [Binding("escape,q,question_mark", "dismiss_help", "Close")]

    def compose(self) -> ComposeResult:
        yield Label("Keyboard Shortcuts", id="help-title")
        yield Label("")
        rows = [
            ("[E]",     "Edit tile config"),
            ("[P]",     "Edit project config"),
            ("[R]",     "New run on selected tile"),
            ("[W]",     "Open waves for selected run"),
            ("[N]",     "New tile in selected database"),
            ("[↑↓]",   "Navigate tree / run list"),
            ("[Enter]", "Expand / collapse database"),
            ("[Esc]",   "Go back / up one level"),
            ("[Q]",     "Quit"),
            ("[?]",     "This help"),
        ]
        for key, desc in rows:
            yield Label(f"  {key:<12} {desc}")
        yield Label("")
        yield Label("  Press Escape or Q to close", style="color: #888888")

    def action_dismiss_help(self) -> None:
        self.dismiss()


# ─── Main App ──────────────────────────────────────────────────────────────────

class VeriFlowApp(App):
    CSS = APP_CSS
    TITLE = "SEMICOLAB · VeriFlow"
    SUB_TITLE = "RTL Verification"

    BINDINGS = [
        Binding("e",             "edit_tile",    "Edit",    show=True),
        Binding("p",             "edit_project", "Project", show=True),
        Binding("r",             "run_tile",     "Run",     show=True),
        Binding("w",             "open_waves",   "Waves",   show=True),
        Binding("n",             "new_tile",     "Nuevo",   show=True),
        Binding("question_mark", "show_help",    "Ayuda",   show=True),
        Binding("q",             "quit_app",     "Salir",   show=True),
        Binding("escape",        "go_back",      "Back",    show=False),
    ]

    def __init__(self, workspace: Path) -> None:
        super().__init__()
        self._workspace = workspace
        self._current_db: Path | None = None
        self._current_tile: dict | None = None
        self._current_runs: list[Path] = []
        self._current_run_dir: Path | None = None

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("workspace", id="breadcrumb")
        with Horizontal(id="main-area"):
            with Vertical(id="nav-panel"):
                yield Label("📁 Databases", id="nav-title")
                yield Tree("root", id="nav-tree")
            with ScrollableContainer(id="detail-panel"):
                yield Label(
                    "Select a tile from the tree to see details.",
                    id="detail-empty",
                )
                with Vertical(id="tile-info"):
                    yield Label("", id="detail-title")
                    yield Label("", id="detail-subtitle")
                    yield Label("", id="detail-version")
                    yield Label("Runs", id="runs-header")
                    yield Label(
                        "  No runs yet — press [R] to start one.",
                        id="runs-empty",
                    )
                    yield ListView(id="runs-list")
                yield Label("", id="workspace-label")
        yield Footer()

    def on_mount(self) -> None:
        tree = self.query_one("#nav-tree", Tree)
        tree.show_root = False
        self._populate_tree()
        self._update_breadcrumb()
        self._check_terminal_size()

    def _check_terminal_size(self) -> None:
        w, h = self.size.width, self.size.height
        if w < 80 or h < 24:
            self.notify(
                f"Terminal too small ({w}×{h}). Minimum 80×24 recommended.",
                severity="warning",
                timeout=5,
            )

    # ── Tree population ────────────────────────────────────────────────────────

    def _populate_tree(self) -> None:
        tree = self.query_one("#nav-tree", Tree)
        tree.clear()

        dbs = _find_databases(self._workspace)
        if not dbs:
            tree.root.add_leaf("  (No databases found)")
            return

        for db in dbs:
            db_node = tree.root.add(
                f"📁 {db.name}",
                data={"type": "db", "path": db},
            )
            for tile in _list_tiles(db):
                name = tile.get("tile_name") or f"tile_{tile.get('tile_number', '?')}"
                db_node.add_leaf(
                    f"  {name}",
                    data={"type": "tile", "db": db, "tile": tile},
                )
            db_node.expand()

    # ── Breadcrumb ─────────────────────────────────────────────────────────────

    def _update_breadcrumb(self) -> None:
        parts = ["workspace"]
        if self._current_db:
            parts.append(self._current_db.name)
        if self._current_tile:
            parts.append(self._current_tile.get("tile_name", "?"))
        self.query_one("#breadcrumb", Label).update(" > ".join(parts))

    # ── Detail panel ──────────────────────────────────────────────────────────

    def _show_tile_info(self, visible: bool) -> None:
        empty = self.query_one("#detail-empty", Label)
        info  = self.query_one("#tile-info", Vertical)
        empty.display = not visible
        info.display  = visible

    def _update_detail(self) -> None:
        tile = self._current_tile
        db   = self._current_db

        if tile is None or db is None:
            self._show_tile_info(False)
            return

        self._show_tile_info(True)

        tile_id   = tile.get("tile_id", "?")
        tile_name = tile.get("tile_name") or f"tile_{tile.get('tile_number', '?')}"
        version   = tile.get("version", "?")
        revision  = tile.get("revision", "?")

        self.query_one("#detail-title",   Label).update(tile_name)
        self.query_one("#detail-subtitle", Label).update(tile_id)
        self.query_one("#detail-version",  Label).update(f"v{version}r{revision}")

        runs = _list_runs(db, tile_id)
        self._current_runs = runs
        self._current_run_dir = None

        runs_list  = self.query_one("#runs-list",  ListView)
        runs_empty = self.query_one("#runs-empty", Label)

        runs_list.clear()
        if not runs:
            runs_empty.display = True
            runs_list.display  = False
        else:
            runs_empty.display = False
            runs_list.display  = True
            for run_dir in runs:
                m      = _run_manifest(run_dir)
                status = m.get("status", "?")
                date   = m.get("date", "")
                icon   = _status_icon(status)
                runs_list.append(ListItem(Label(f"{icon}  {run_dir.name}  {status}  {date}")))

        host_ws = os.environ.get("HOST_WORKSPACE", str(self._workspace))
        self.query_one("#workspace-label", Label).update(f"\nWorkspace: {host_ws}")

    # ── Tree events ────────────────────────────────────────────────────────────

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        data = event.node.data
        if data is None:
            return
        if data.get("type") == "tile":
            self._current_db   = data["db"]
            self._current_tile = data["tile"]
            self._current_runs = []
            self._current_run_dir = None
            self._update_breadcrumb()
            self._update_detail()
        elif data.get("type") == "db":
            self._current_db   = data["path"]
            self._current_tile = None
            self._current_runs = []
            self._current_run_dir = None
            self._update_breadcrumb()

    # ── ListView events ────────────────────────────────────────────────────────

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id != "runs-list":
            return
        idx = event.list_view.index
        if idx is not None and 0 <= idx < len(self._current_runs):
            self._current_run_dir = self._current_runs[idx]

    # ── Actions ────────────────────────────────────────────────────────────────

    def action_run_tile(self) -> None:
        if not self._current_tile or not self._current_db:
            self.notify("Select a tile first.", severity="warning")
            return
        tile_number = self._current_tile.get("tile_number", "")
        cmd = ["veriflow", "--db", str(self._current_db), "run", "--tile", tile_number]
        with self.suspend():
            subprocess.run(cmd)
        self._update_detail()

    def action_open_waves(self) -> None:
        if not self._current_run_dir:
            self.notify("Select a run from the list first.", severity="warning")
            return
        if not self._current_tile or not self._current_db:
            return
        tile_number = self._current_tile.get("tile_number", "")
        cmd = [
            "veriflow", "--db", str(self._current_db),
            "waves", "--tile", tile_number, "--run", self._current_run_dir.name,
        ]
        with self.suspend():
            subprocess.run(cmd)

    def action_new_tile(self) -> None:
        if not self._current_db:
            self.notify("Select a database first.", severity="warning")
            return
        cmd = ["veriflow", "--db", str(self._current_db), "create-tile"]
        with self.suspend():
            subprocess.run(cmd)
        self._populate_tree()
        self._update_detail()

    def action_edit_tile(self) -> None:
        if not self._current_tile or not self._current_db:
            self.notify("Select a tile first.", severity="warning")
            return
        tile_number  = self._current_tile.get("tile_number", "")
        config_path  = _tile_config_path(self._current_db, tile_number)
        self.push_screen(
            EditTileScreen(config_path, _read_yaml(config_path)),
            self._on_tile_saved,
        )

    def _on_tile_saved(self, saved: bool) -> None:
        if saved:
            self.notify("Tile config saved.", severity="information")
            self._populate_tree()
            self._update_detail()

    def action_edit_project(self) -> None:
        if not self._current_db:
            self.notify("Select a database first.", severity="warning")
            return
        config_path = self._current_db / "project_config.yaml"
        self.push_screen(
            EditProjectScreen(config_path, _read_yaml(config_path)),
            self._on_project_saved,
        )

    def _on_project_saved(self, saved: bool) -> None:
        if saved:
            self.notify("Project config saved.", severity="information")

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_go_back(self) -> None:
        tree = self.query_one("#nav-tree", Tree)
        node = tree.cursor_node
        if node is None or node.parent is None or node.parent.is_root:
            self.exit()
        else:
            tree.move_cursor(node.parent)

    def action_quit_app(self) -> None:
        self.exit()


# ─── Entry point ───────────────────────────────────────────────────────────────

def run_tui(workspace: Path = Path(".")) -> None:
    VeriFlowApp(workspace).run()

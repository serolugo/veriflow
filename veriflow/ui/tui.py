"""
veriflow.ui.tui  (v2 — 3-column ranger/Argonaut navigator)
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Label, ListItem, ListView

from .themes import (
    THEME_LABELS,
    THEMES,
    build_css_vars,
    get_palette,
    load_theme,
    palette_to_vars,
    save_theme,
)


# ─── Data helpers ─────────────────────────────────────────────────────────────

def _find_databases(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(
        p for p in root.iterdir()
        if p.is_dir() and (p / "project_config.yaml").exists()
    )


def _list_tiles(db: Path) -> list[dict]:
    import csv
    index = db / "tile_index.csv"
    if not index.exists():
        return []
    with open(index, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _list_runs(db: Path, tile_id: str) -> list[Path]:
    runs_dir = db / "tiles" / tile_id / "runs"
    if not runs_dir.exists():
        return []
    return sorted(
        (d for d in runs_dir.iterdir() if d.is_dir() and d.name.startswith("run-")),
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


# ─── CSS ──────────────────────────────────────────────────────────────────────
# Uses var(--tb-X) CSS variables injected via App.get_css_variables().
# Changing the theme calls refresh_css() which re-resolves all variables.

_APP_CSS = build_css_vars() + """
#breadcrumb {
    height: 1;
    background: var(--tb-bg-muted);
    color: var(--tb-blue);
    padding: 0 2;
    text-style: bold;
}

#columns {
    height: 1fr;
    padding: 0 1;
}

.col {
    border: round var(--tb-border);
    margin: 0 1;
    height: 1fr;
}

.col.active {
    border: round var(--tb-accent);
}

#col-db   { width: 26; }
#col-tile { width: 1fr; }
#col-run  { width: 2fr; }

#db-empty {
    display: none;
    width: 1fr;
    height: 1fr;
    align: center middle;
    padding: 1 2;
    color: var(--tb-text-dim);
}

#btn-init {
    margin-top: 1;
    background: var(--tb-orange);
    color: var(--tb-bg);
    border: none;
    width: 100%;
}

#btn-init:focus {
    background: var(--tb-yellow);
}

#form-scroll { padding: 2 4; }
#form-title  { color: var(--tb-orange); text-style: bold; margin-bottom: 1; }
.field-label { color: var(--tb-text-dim); height: 1; }

Input {
    margin-bottom: 1;
    background: var(--tb-bg-muted);
    border: tall var(--tb-border);
    color: var(--tb-text);
}
Input:focus { border: tall var(--tb-orange); }

#btn-row   { margin-top: 1; height: 3; layout: horizontal; }
Button     { margin-right: 2; }
#btn-save   { background: var(--tb-orange);   color: var(--tb-bg); border: none; }
#btn-cancel { background: var(--tb-bg-muted); color: var(--tb-text); border: none; }
#btn-yes    { background: var(--tb-red);      color: var(--tb-bg); border: none; }
#btn-no     { background: var(--tb-bg-muted); color: var(--tb-text); border: none; }

#help-title { color: var(--tb-orange); text-style: bold; margin-bottom: 1; }

#confirm-box {
    background: var(--tb-bg-muted);
    border: round var(--tb-accent);
    padding: 2 4;
    width: 50;
    height: auto;
    align: center middle;
}
#confirm-msg { color: var(--tb-text); margin-bottom: 1; }

/* Theme picker */
#theme-list {
    height: 1fr;
    width: 1fr;
    background: var(--tb-bg);
}
#theme-title { color: var(--tb-orange); text-style: bold; margin-bottom: 1; }
#theme-hint  { color: var(--tb-text-dim); margin-top: 1; }
"""


# ─── Form screens (unchanged from v1) ─────────────────────────────────────────

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

PROJECT_CONFIG_FIELDS: list[tuple[str, str]] = [
    ("id_prefix",    "ID Prefix"),
    ("project_name", "Project Name"),
    ("repo",         "Repository"),
    ("description",  "Description"),
]


class AskInputScreen(Screen):
    CSS = "Screen { background: #1a1b26; color: #c0caf5; }"
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, title: str, prompt: str, placeholder: str = "") -> None:
        super().__init__()
        self._title       = title
        self._prompt      = prompt
        self._placeholder = placeholder

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="form-scroll"):
            yield Label(self._title,  id="form-title")
            yield Label(self._prompt, classes="field-label")
            yield Input(placeholder=self._placeholder, id="ask-input")
            with Horizontal(id="btn-row"):
                yield Button("OK",     id="btn-save")
                yield Button("Cancel", id="btn-cancel")

    def on_mount(self) -> None:
        self.query_one("#ask-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self._submit()
        else:
            self.dismiss(None)

    def on_input_submitted(self, _: Input.Submitted) -> None:
        self._submit()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _submit(self) -> None:
        value = self.query_one("#ask-input", Input).value.strip()
        self.dismiss(value if value else None)


class EditTileScreen(Screen):
    CSS = "Screen { background: #1a1b26; color: #c0caf5; }"
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, config_path: Path, initial: dict) -> None:
        super().__init__()
        self._config_path = config_path
        self._initial     = initial

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="form-scroll"):
            yield Label("Edit Tile Config", id="form-title")
            for key, label in TILE_CONFIG_FIELDS:
                yield Label(label, classes="field-label")
                yield Input(value=str(self._initial.get(key, "") or ""), id=f"f-{key}")
            with Horizontal(id="btn-row"):
                yield Button("Save",   id="btn-save")
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


class EditProjectScreen(Screen):
    CSS = "Screen { background: #1a1b26; color: #c0caf5; }"
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, config_path: Path, initial: dict) -> None:
        super().__init__()
        self._config_path = config_path
        self._initial     = initial

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="form-scroll"):
            yield Label("Edit Project Config", id="form-title")
            for key, label in PROJECT_CONFIG_FIELDS:
                yield Label(label, classes="field-label")
                yield Input(value=str(self._initial.get(key, "") or ""), id=f"f-{key}")
            with Horizontal(id="btn-row"):
                yield Button("Save",   id="btn-save")
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


class ConfirmScreen(Screen):
    CSS = """
    Screen { background: #00000088; align: center middle; }
    """
    BINDINGS = [
        Binding("y",      "yes",  "Yes"),
        Binding("n",      "no",   "No"),
        Binding("escape", "no",   "No"),
    ]

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Label(self._message, id="confirm-msg")
            with Horizontal(id="btn-row"):
                yield Button("Sí [Y]", id="btn-yes")
                yield Button("No [N]", id="btn-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-yes")

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)


class ThemeScreen(Screen):
    CSS = "Screen { background: var(--tb-bg); color: var(--tb-text); padding: 2 4; }"
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        yield Label("Seleccionar Tema", id="theme-title")
        lv = ListView(id="theme-list")
        yield lv
        yield Label("↑↓ navegar · Enter seleccionar · Esc cancelar", id="theme-hint")

    def on_mount(self) -> None:
        lv      = self.query_one("#theme-list", ListView)
        current = load_theme()
        for key, label in THEME_LABELS.items():
            marker = " ●" if key == current else ""
            lv.append(ListItem(Label(f"  {label}{marker}"), name=key))
        lv.focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.item.name)

    def action_cancel(self) -> None:
        self.dismiss(None)


class HelpScreen(Screen):
    CSS = "Screen { background: var(--tb-bg); color: var(--tb-text); padding: 2 4; }"
    BINDINGS = [Binding("escape,q,question_mark", "dismiss_help", "Close")]

    def compose(self) -> ComposeResult:
        yield Label("Keyboard Shortcuts", id="help-title")
        yield Label("")
        rows = [
            ("→ / Enter",  "Avanzar al siguiente panel / seleccionar"),
            ("← / Esc",    "Retroceder al panel anterior"),
            ("[I]",        "Init database"),
            ("[N]",        "Nuevo tile en la database activa"),
            ("[E]",        "Editar tile config"),
            ("[P]",        "Editar project config"),
            ("[R]",        "Ejecutar run en el tile activo"),
            ("[W]",        "Abrir waves del run activo"),
            ("[B]",        "Mostrar path del workspace"),
            ("[T]",        "Cambiar tema"),
            ("[↑↓]",       "Navegar dentro del panel activo"),
            ("[Q]",        "Salir"),
            ("[?]",        "Esta ayuda"),
        ]
        for key, desc in rows:
            yield Label(f"  {key:<16} {desc}")
        yield Label("")
        yield Label("  Press Esc to close", style="color: var(--tb-text-dim)")

    def action_dismiss_help(self) -> None:
        self.dismiss()


# ─── Main App ─────────────────────────────────────────────────────────────────

_COL_IDS = ("col-db", "col-tile", "col-run")
_LV_IDS  = ("lv-db",  "lv-tile",  "lv-run")
_TITLES  = ("📁  Databases", "🧩  Tiles", "🏃  Runs")


class VeriFlowApp(App):
    CSS   = _APP_CSS
    TITLE = "SEMICOLAB · VeriFlow"

    BINDINGS = [
        Binding("i",             "init_db",      "Init",    show=True),
        Binding("e",             "edit_tile",    "Edit",    show=True),
        Binding("p",             "edit_project", "Project", show=True),
        Binding("n",             "new_tile",     "Nuevo",   show=True),
        Binding("r",             "run_tile",     "Run",     show=True),
        Binding("w",             "open_waves",   "Waves",   show=True),
        Binding("b",             "show_path",    "Path",    show=True),
        Binding("t",             "pick_theme",   "Tema",    show=True),
        Binding("question_mark", "show_help",    "Ayuda",   show=True),
        Binding("q",             "quit_app",     "Salir",   show=True),
        Binding("right",         "go_right",     "",        show=False),
        Binding("left",          "go_left",      "",        show=False),
        Binding("escape",        "go_left",      "",        show=False),
    ]

    def __init__(self, workspace: Path) -> None:
        super().__init__()
        self._workspace   = workspace
        self._theme: str  = load_theme()
        self._col         = 0
        self._db:    Path | None = None
        self._tile:  dict | None = None
        self._run:   Path | None = None
        self._dbs:   list[Path] = []
        self._tiles: list[dict] = []
        self._runs:  list[Path] = []
        self._loading = False

    def get_css_variables(self) -> dict[str, str]:
        return {**super().get_css_variables(), **palette_to_vars(get_palette(self._theme))}

    # ── Layout ───────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Label("", id="breadcrumb")
        with Horizontal(id="columns"):
            with Vertical(id="col-db", classes="col active"):
                yield ListView(id="lv-db")
                with Vertical(id="db-empty"):
                    yield Label("No hay databases todavía.")
                    yield Button("[ I · Init Database ]", id="btn-init")
            with Vertical(id="col-tile", classes="col"):
                yield ListView(id="lv-tile")
                yield Label(
                    "← Selecciona una database",
                    id="tile-empty",
                    classes="col-empty",
                )
            with Vertical(id="col-run", classes="col"):
                yield ListView(id="lv-run")
                yield Label(
                    "← Selecciona un tile",
                    id="run-empty",
                    classes="col-empty",
                )
        yield Footer()

    def on_mount(self) -> None:
        for i, cid in enumerate(_COL_IDS):
            self.query_one(f"#{cid}").border_title = _TITLES[i]
        self._populate_dbs()
        self._update_breadcrumb()
        self.query_one("#lv-db", ListView).focus()
        self._check_size()

    def _check_size(self) -> None:
        w, h = self.size.width, self.size.height
        if w < 80 or h < 24:
            self.notify(
                f"Terminal pequeña ({w}×{h}). Mínimo 80×24.",
                severity="warning",
                timeout=5,
            )

    # ── Population ───────────────────────────────────────────────────────────

    def _populate_dbs(self) -> None:
        self._loading = True
        try:
            self._dbs = _find_databases(self._workspace)
            lv        = self.query_one("#lv-db",   ListView)
            db_empty  = self.query_one("#db-empty")
            lv.clear()

            if not self._dbs:
                lv.display       = False
                db_empty.display = True
                self._tiles = []
                self._runs  = []
                self._clear_lv("lv-tile", "tile-empty", "← Selecciona una database")
                self._clear_lv("lv-run",  "run-empty",  "← Selecciona un tile")
                return

            lv.display       = True
            db_empty.display = False
            for db in self._dbs:
                lv.append(ListItem(Label(f"  {db.name}")))

            self._db = self._dbs[0]
            self._populate_tiles(self._dbs[0])
        finally:
            self._loading = False

    def _populate_tiles(self, db: Path) -> None:
        self._tiles = _list_tiles(db)
        lv          = self.query_one("#lv-tile", ListView)
        empty       = self.query_one("#tile-empty", Label)
        lv.clear()

        if not self._tiles:
            lv.display    = False
            empty.display = True
            empty.update("No hay tiles — presiona [N].")
            self._runs = []
            self._clear_lv("lv-run", "run-empty", "← Selecciona un tile")
            return

        lv.display    = True
        empty.display = False
        for tile in self._tiles:
            name = tile.get("tile_name") or f"tile_{tile.get('tile_number', '?')}"
            ver  = str(tile.get("version",  "")).zfill(2)
            rev  = str(tile.get("revision", "")).zfill(2)
            lv.append(ListItem(Label(f"  {name}  v{ver}r{rev}")))

        if self._tiles:
            self._tile = self._tiles[0]
            self._populate_runs(db, self._tiles[0])

    def _populate_runs(self, db: Path, tile: dict) -> None:
        tile_id    = tile.get("tile_id", "")
        self._runs = _list_runs(db, tile_id)
        lv         = self.query_one("#lv-run", ListView)
        empty      = self.query_one("#run-empty", Label)
        lv.clear()

        if not self._runs:
            lv.display    = False
            empty.display = True
            empty.update("No hay runs — presiona [R].")
            return

        lv.display    = True
        empty.display = False
        for run_dir in self._runs:
            m      = _run_manifest(run_dir)
            status = m.get("status", "?")
            date   = str(m.get("date", ""))[:10]
            icon   = _status_icon(status)
            css    = {"PASS": "run-pass", "FAIL": "run-fail"}.get(status, "run-warn")
            lv.append(ListItem(Label(
                f"  {icon}  {run_dir.name}  {date}",
                classes=css,
            )))

    def _clear_lv(self, lv_id: str, empty_id: str, msg: str) -> None:
        lv    = self.query_one(f"#{lv_id}",  ListView)
        empty = self.query_one(f"#{empty_id}", Label)
        lv.clear()
        lv.display    = False
        empty.display = True
        empty.update(msg)

    # ── Column focus ─────────────────────────────────────────────────────────

    def _set_col(self, col: int) -> None:
        for i, cid in enumerate(_COL_IDS):
            c = self.query_one(f"#{cid}")
            if i == col:
                c.add_class("active")
            else:
                c.remove_class("active")
        self._col = col
        lv = self.query_one(f"#{_LV_IDS[col]}", ListView)
        if lv.display:
            lv.focus()

    # ── Breadcrumb ────────────────────────────────────────────────────────────

    def _update_breadcrumb(self) -> None:
        parts = ["workspace", "veriflow"]
        if self._db:
            parts.append(self._db.name)
        if self._tile:
            parts.append(self._tile.get("tile_name", "?"))
        if self._run:
            parts.append(self._run.name)
        self.query_one("#breadcrumb", Label).update(" > ".join(parts))

    # ── Events ───────────────────────────────────────────────────────────────

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if self._loading:
            return
        lv_id = event.list_view.id
        idx   = event.list_view.index
        if idx is None:
            return

        self._loading = True
        try:
            if lv_id == "lv-db" and 0 <= idx < len(self._dbs):
                self._db   = self._dbs[idx]
                self._tile = None
                self._run  = None
                self._populate_tiles(self._db)
                self._update_breadcrumb()

            elif lv_id == "lv-tile" and 0 <= idx < len(self._tiles):
                self._tile = self._tiles[idx]
                self._run  = None
                if self._db:
                    self._populate_runs(self._db, self._tile)
                self._update_breadcrumb()

            elif lv_id == "lv-run" and 0 <= idx < len(self._runs):
                self._run = self._runs[idx]
                self._update_breadcrumb()
        finally:
            self._loading = False

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == _LV_IDS[self._col]:
            self.action_go_right()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-init":
            self.action_init_db()

    # ── Navigation actions ────────────────────────────────────────────────────

    def action_go_right(self) -> None:
        if self._col == 0:
            if not self._db or not self._tiles:
                self.notify("No hay tiles — presiona [N].", severity="warning")
                return
            self._set_col(1)
        elif self._col == 1:
            if not self._tile or not self._runs:
                self.notify("No hay runs — presiona [R].", severity="warning")
                return
            self._set_col(2)

    def action_go_left(self) -> None:
        if self._col == 2:
            self._set_col(1)
        elif self._col == 1:
            self._set_col(0)
        elif self._col == 0:
            self.push_screen(
                ConfirmScreen("¿Salir de VeriFlow?"),
                lambda ok: self.exit() if ok else None,
            )

    # ── Command actions ───────────────────────────────────────────────────────

    def action_init_db(self) -> None:
        self.push_screen(
            AskInputScreen("Init Database", "Nombre de la nueva database:", "mi_proyecto"),
            self._on_init_name,
        )

    def _on_init_name(self, name: str | None) -> None:
        if not name:
            return
        db_path = self._workspace / name
        with self.suspend():
            subprocess.run(["veriflow", "--db", str(db_path), "init"])
        self._db = self._tile = self._run = None
        self._populate_dbs()
        self._update_breadcrumb()

    def action_new_tile(self) -> None:
        if not self._db:
            self.notify("Selecciona una database primero.", severity="warning")
            return
        with self.suspend():
            subprocess.run(["veriflow", "--db", str(self._db), "create-tile"])
        self._populate_tiles(self._db)
        self._update_breadcrumb()

    def action_run_tile(self) -> None:
        if not self._tile or not self._db:
            self.notify("Selecciona un tile primero.", severity="warning")
            return
        tile_number = self._tile.get("tile_number", "")
        with self.suspend():
            subprocess.run(["veriflow", "--db", str(self._db), "run", "--tile", tile_number])
        if self._tile:
            self._populate_runs(self._db, self._tile)

    def action_open_waves(self) -> None:
        if not self._run:
            self.notify("Selecciona un run primero.", severity="warning")
            return
        tile_number = self._tile.get("tile_number", "")
        with self.suspend():
            subprocess.run([
                "veriflow", "--db", str(self._db),
                "waves", "--tile", tile_number, "--run", self._run.name,
            ])

    def action_edit_tile(self) -> None:
        if not self._tile or not self._db:
            self.notify("Selecciona un tile primero.", severity="warning")
            return
        tile_number = self._tile.get("tile_number", "")
        config_path = _tile_config_path(self._db, tile_number)
        self.push_screen(
            EditTileScreen(config_path, _read_yaml(config_path)),
            self._on_tile_saved,
        )

    def _on_tile_saved(self, saved: bool) -> None:
        if saved:
            self.notify("Tile config guardado.", severity="information")
            self._populate_tiles(self._db)

    def action_edit_project(self) -> None:
        if not self._db:
            self.notify("Selecciona una database primero.", severity="warning")
            return
        config_path = self._db / "project_config.yaml"
        self.push_screen(
            EditProjectScreen(config_path, _read_yaml(config_path)),
            lambda saved: self.notify("Project config guardado.") if saved else None,
        )

    def action_show_path(self) -> None:
        host_ws = os.environ.get("HOST_WORKSPACE", str(self._workspace))
        self.notify(f"Workspace: {host_ws}", timeout=6)

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_pick_theme(self) -> None:
        self.push_screen(ThemeScreen(), self._on_theme_selected)

    def _on_theme_selected(self, name: str | None) -> None:
        if not name or name == self._theme:
            return
        self._theme = name
        save_theme(name)
        try:
            self.refresh_css()
        except AttributeError:
            # Fallback for older Textual versions
            self.notify(
                f"Tema '{THEME_LABELS.get(name, name)}' guardado. Reinicia para aplicar.",
                severity="information",
                timeout=4,
            )
            return
        label = THEME_LABELS.get(name, name)
        self.notify(f"Tema: {label}", severity="information", timeout=2)

    def action_quit_app(self) -> None:
        self.push_screen(
            ConfirmScreen("¿Salir de VeriFlow?"),
            lambda ok: self.exit() if ok else None,
        )


# ─── Entry point ──────────────────────────────────────────────────────────────

def run_tui(workspace: Path = Path(".")) -> None:
    VeriFlowApp(workspace).run()

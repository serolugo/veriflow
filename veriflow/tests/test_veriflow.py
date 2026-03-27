"""
VeriFlow V1 — Integration tests.
Uses tempfile.mkdtemp() for isolated environments. Cleans up after each test.
"""

import shutil
import tempfile
from datetime import date
from pathlib import Path

# ── helpers ──────────────────────────────────────────────────────────────────

def _make_db(tmp: Path) -> Path:
    """Initialize a fresh database inside tmp."""
    db = tmp / "database"
    from veriflow.commands.init_db import cmd_init
    cmd_init(db)
    return db


def _fill_project_config(db: Path, id_prefix: str = "TST-01") -> None:
    import yaml
    cfg = {
        "id_prefix": id_prefix,
        "project_name": "Test Project",
        "repo": "https://github.com/test/test",
        "description": "Test project for VeriFlow unit tests.\n",
    }
    (db / "project_config.yaml").write_text(
        "\n".join(f"{k}: {v!r}" if isinstance(v, str) and "\n" not in v
                  else (f"{k}: |\n  {v.strip()}" if "\n" in v else f"{k}: {v!r}")
                  for k, v in cfg.items()),
        encoding="utf-8",
    )
    # Use simple yaml.dump instead
    import yaml
    (db / "project_config.yaml").write_text(yaml.dump(cfg, default_flow_style=False), encoding="utf-8")


def _add_rtl(db: Path, tile_number_str: str, module_name: str = "my_tile") -> None:
    """Write a minimal valid RTL file for the given tile."""
    rtl_dir = db / "config" / f"tile_{tile_number_str}" / "src" / "rtl"
    rtl_dir.mkdir(parents=True, exist_ok=True)
    rtl = rtl_dir / f"{module_name}.v"
    rtl.write_text(f"""`timescale 1ns/1ps
module {module_name} #(
    parameter REG_WIDTH = 32,
    parameter CSR_IN_WIDTH = 16,
    parameter CSR_OUT_WIDTH = 16
)(
    input  wire clk,
    input  wire arst_n,
    input  wire [CSR_IN_WIDTH-1:0]  csr_in,
    input  wire [REG_WIDTH-1:0]     data_reg_a,
    input  wire [REG_WIDTH-1:0]     data_reg_b,
    output wire [REG_WIDTH-1:0]     data_reg_c,
    output wire [CSR_OUT_WIDTH-1:0] csr_out,
    output wire                     csr_in_re,
    output wire                     csr_out_we
);
    assign data_reg_c = data_reg_a + data_reg_b;
    assign csr_out    = csr_in;
    assign csr_in_re  = 1'b0;
    assign csr_out_we = 1'b0;
endmodule
""", encoding="utf-8")


def _fill_tile_config(db: Path, tile_number_str: str, module_name: str = "my_tile") -> None:
    import yaml
    cfg_path = db / "config" / f"tile_{tile_number_str}" / "tile_config.yaml"
    cfg = {
        "tile_name": "Test Tile",
        "tile_author": "Tester",
        "top_module": module_name,
        "description": "A test tile.",
        "ports": "Standard ports.",
        "usage_guide": "Just run it.",
        "tb_description": "Basic TB.",
    }
    cfg_path.write_text(yaml.dump(cfg, default_flow_style=False), encoding="utf-8")


def _fill_run_config(db: Path, tile_number_str: str) -> None:
    import yaml
    cfg_path = db / "config" / f"tile_{tile_number_str}" / "run_config.yaml"
    cfg = {
        "run_author": "Tester",
        "objective": "Test run",
        "tags": "test",
        "main_change": "Initial.",
        "notes": "No notes.",
    }
    cfg_path.write_text(yaml.dump(cfg, default_flow_style=False), encoding="utf-8")


# ── test functions ────────────────────────────────────────────────────────────

def test_tile_id_generation():
    from veriflow.core.tile_id import generate_tile_id
    tid = generate_tile_id("MST130-01", 1, 1, 1, today=date(2026, 3, 15))
    assert tid == "MST130-01-26031500010101", f"Got: {tid}"


def test_tile_id_parsing():
    from veriflow.core.tile_id import parse_tile_id
    p = parse_tile_id("MST130-01-26031500010101")
    assert p["id_prefix"] == "MST130-01"
    assert p["tile_number"] == 1
    assert p["id_version"] == 1
    assert p["id_revision"] == 1
    assert p["yymmdd"] == "260315"


def test_run_id_first():
    from veriflow.core.run_id import get_next_run_id
    tmp = Path(tempfile.mkdtemp())
    try:
        runs_dir = tmp / "runs"
        runs_dir.mkdir()
        rid = get_next_run_id(runs_dir)
        assert rid == "run-001", f"Got: {rid}"
    finally:
        shutil.rmtree(tmp)


def test_run_id_increment():
    from veriflow.core.run_id import get_next_run_id
    tmp = Path(tempfile.mkdtemp())
    try:
        runs_dir = tmp / "runs"
        runs_dir.mkdir()
        (runs_dir / "run-001").mkdir()
        (runs_dir / "run-002").mkdir()
        rid = get_next_run_id(runs_dir)
        assert rid == "run-003", f"Got: {rid}"
    finally:
        shutil.rmtree(tmp)


def test_init_creates_structure():
    tmp = Path(tempfile.mkdtemp())
    try:
        db = tmp / "db"
        from veriflow.commands.init_db import cmd_init
        cmd_init(db)
        assert (db / "project_config.yaml").exists()
        assert (db / "tile_index.csv").exists()
        assert (db / "records.csv").exists()
        assert (db / "tiles").is_dir()
        assert (db / "config").is_dir()
        assert (db / "tiles" / ".gitkeep").exists()
    finally:
        shutil.rmtree(tmp)


def test_init_force():
    tmp = Path(tempfile.mkdtemp())
    try:
        db = tmp / "db"
        from veriflow.commands.init_db import cmd_init
        cmd_init(db)
        cmd_init(db, force=True)  # should not raise
        assert (db / "project_config.yaml").exists()
    finally:
        shutil.rmtree(tmp)


def test_init_no_force_raises():
    tmp = Path(tempfile.mkdtemp())
    try:
        db = tmp / "db"
        from veriflow.commands.init_db import cmd_init
        from veriflow.core import VeriFlowError
        cmd_init(db)
        raised = False
        try:
            cmd_init(db, force=False)
        except VeriFlowError:
            raised = True
        assert raised, "Expected VeriFlowError when database exists without --force"
    finally:
        shutil.rmtree(tmp)


def test_create_tile_structure():
    tmp = Path(tempfile.mkdtemp())
    try:
        db = _make_db(tmp)
        _fill_project_config(db)
        from veriflow.commands.create_tile import cmd_create_tile
        cmd_create_tile(db)

        # Check config dir
        cfg_dir = db / "config" / "tile_0001"
        assert cfg_dir.exists()
        assert (cfg_dir / "tile_config.yaml").exists()
        assert (cfg_dir / "run_config.yaml").exists()
        assert (cfg_dir / "src" / "rtl").is_dir()
        assert (cfg_dir / "src" / "tb").is_dir()

        # Check tile_index row
        from veriflow.core.csv_store import read_tile_index
        rows = read_tile_index(db / "tile_index.csv")
        assert len(rows) == 1
        assert rows[0]["tile_number"] == "0001"
        assert rows[0]["version"] == "01"
        assert rows[0]["revision"] == "01"
    finally:
        shutil.rmtree(tmp)


def test_create_tile_tiles_dir():
    tmp = Path(tempfile.mkdtemp())
    try:
        db = _make_db(tmp)
        _fill_project_config(db)
        from veriflow.commands.create_tile import cmd_create_tile
        cmd_create_tile(db)
        from veriflow.core.csv_store import read_tile_index
        rows = read_tile_index(db / "tile_index.csv")
        tile_id = rows[0]["tile_id"]
        tile_dir = db / "tiles" / tile_id
        assert tile_dir.is_dir()
        assert (tile_dir / "README.md").exists()
        assert (tile_dir / "works" / "rtl").is_dir()
        assert (tile_dir / "works" / "tb").is_dir()
        assert (tile_dir / "runs").is_dir()
    finally:
        shutil.rmtree(tmp)


def test_csv_empty_file_rule():
    """Empty CSV gets header written before first append."""
    tmp = Path(tempfile.mkdtemp())
    try:
        db = _make_db(tmp)
        _fill_project_config(db)
        from veriflow.commands.create_tile import cmd_create_tile
        cmd_create_tile(db)

        tile_index = db / "tile_index.csv"
        content = tile_index.read_text(encoding="utf-8")
        assert "tile_number" in content
        assert "tile_id" in content
    finally:
        shutil.rmtree(tmp)


def test_csv_header_validation():
    from veriflow.core import VeriFlowError
    from veriflow.core.csv_store import read_tile_index
    tmp = Path(tempfile.mkdtemp())
    try:
        bad_csv = tmp / "tile_index.csv"
        bad_csv.write_text("wrong,header,here\n1,X,Y\n", encoding="utf-8")
        raised = False
        try:
            read_tile_index(bad_csv)
        except VeriFlowError:
            raised = True
        assert raised, "Expected VeriFlowError for bad CSV header"
    finally:
        shutil.rmtree(tmp)


def test_flat_copy_basic():
    from veriflow.core.copier import copy_flat
    tmp = Path(tempfile.mkdtemp())
    try:
        src = tmp / "src"
        src.mkdir()
        (src / "a.v").write_text("module a; endmodule", encoding="utf-8")
        (src / "b.v").write_text("module b; endmodule", encoding="utf-8")
        dst = tmp / "dst"
        copied = copy_flat(src, dst)
        assert len(copied) == 2
        assert (dst / "a.v").exists()
        assert (dst / "b.v").exists()
    finally:
        shutil.rmtree(tmp)


def test_flat_copy_collision():
    from veriflow.core.copier import copy_flat
    tmp = Path(tempfile.mkdtemp())
    try:
        src1 = tmp / "src1"
        src1.mkdir()
        (src1 / "tile.v").write_text("module a; endmodule", encoding="utf-8")

        dst = tmp / "dst"
        copy_flat(src1, dst)

        # Second copy of same name should get _1 suffix
        src2 = tmp / "src2"
        src2.mkdir()
        (src2 / "tile.v").write_text("module b; endmodule", encoding="utf-8")
        copy_flat(src2, dst)

        assert (dst / "tile.v").exists()
        assert (dst / "tile_1.v").exists()
    finally:
        shutil.rmtree(tmp)


def test_bump_version():
    tmp = Path(tempfile.mkdtemp())
    try:
        db = _make_db(tmp)
        _fill_project_config(db)
        from veriflow.commands.create_tile import cmd_create_tile
        cmd_create_tile(db)
        from veriflow.core.csv_store import get_tile_row
        row_before = get_tile_row(db / "tile_index.csv", "0001")
        old_id = row_before["tile_id"]

        from veriflow.commands.bump_version import cmd_bump_version
        cmd_bump_version(db, "0001")

        row_after = get_tile_row(db / "tile_index.csv", "0001")
        new_id = row_after["tile_id"]
        assert new_id != old_id
        assert row_after["version"] == "02"
        assert row_after["revision"] == "01"  # revision unchanged

        # Old dir preserved, new dir created
        assert (db / "tiles" / old_id).exists()
        assert (db / "tiles" / new_id).exists()
        # New dir has clean runs/
        assert (db / "tiles" / new_id / "runs").exists()
        assert not any((db / "tiles" / new_id / "runs").glob("run-*"))
    finally:
        shutil.rmtree(tmp)


def test_bump_revision():
    tmp = Path(tempfile.mkdtemp())
    try:
        db = _make_db(tmp)
        _fill_project_config(db)
        from veriflow.commands.create_tile import cmd_create_tile
        cmd_create_tile(db)
        from veriflow.core.csv_store import get_tile_row
        row_before = get_tile_row(db / "tile_index.csv", "0001")
        old_id = row_before["tile_id"]

        from veriflow.commands.bump_revision import cmd_bump_revision
        cmd_bump_revision(db, "0001")

        row_after = get_tile_row(db / "tile_index.csv", "0001")
        new_id = row_after["tile_id"]
        assert new_id != old_id
        assert row_after["revision"] == "02"
        assert row_after["version"] == "01"   # version reset to 01

        # Old dir preserved, new dir created
        assert (db / "tiles" / old_id).exists()
        assert (db / "tiles" / new_id).exists()
        # New dir has clean runs/
        assert (db / "tiles" / new_id / "runs").exists()
        assert not any((db / "tiles" / new_id / "runs").glob("run-*"))
    finally:
        shutil.rmtree(tmp)


def test_validation_missing_project_config():
    from veriflow.core import VeriFlowError
    from veriflow.core.validator import validate_database
    tmp = Path(tempfile.mkdtemp())
    try:
        db = tmp / "db"
        db.mkdir()
        raised = False
        try:
            validate_database(db)
        except VeriFlowError:
            raised = True
        assert raised
    finally:
        shutil.rmtree(tmp)


def test_validation_empty_id_prefix():
    from veriflow.core import VeriFlowError
    from veriflow.core.validator import validate_project_config
    from veriflow.models.project_config import ProjectConfig
    raised = False
    try:
        validate_project_config(ProjectConfig(id_prefix="", project_name="X", repo="", description=""))
    except VeriFlowError:
        raised = True
    assert raised


def test_validation_missing_top_module():
    from veriflow.core import VeriFlowError
    tmp = Path(tempfile.mkdtemp())
    try:
        db = _make_db(tmp)
        _fill_project_config(db)
        from veriflow.commands.create_tile import cmd_create_tile
        cmd_create_tile(db)
        _add_rtl(db, "0001", "my_tile")
        # tile_config has empty top_module
        from veriflow.core.validator import validate_run_inputs
        from veriflow.models.tile_config import TileConfig
        tc = TileConfig.from_dict({})  # top_module = ""
        raised = False
        try:
            validate_run_inputs(db, "0001", tc)
        except VeriFlowError:
            raised = True
        assert raised
    finally:
        shutil.rmtree(tmp)


def test_run_creates_structure():
    """
    Test that cmd_run creates the run directory structure and generates docs.
    Skips actual tool execution (--skip-check, --skip-sim, --skip-synth).
    """
    tmp = Path(tempfile.mkdtemp())
    try:
        db = _make_db(tmp)
        _fill_project_config(db)
        from veriflow.commands.create_tile import cmd_create_tile
        cmd_create_tile(db)
        _add_rtl(db, "0001", "my_tile")
        _fill_tile_config(db, "0001", "my_tile")
        _fill_run_config(db, "0001")

        from veriflow.commands.run import cmd_run
        cmd_run(
            db=db,
            tile_number="0001",
            skip_check=True,
            skip_sim=True,
            skip_synth=True,
        )

        from veriflow.core.csv_store import get_tile_row
        row = get_tile_row(db / "tile_index.csv", "0001")
        tile_id = row["tile_id"]
        tile_dir = db / "tiles" / tile_id
        run_dir = tile_dir / "runs" / "run-001"

        assert run_dir.exists(), f"run-001 not found at {run_dir}"
        assert (run_dir / "manifest.yaml").exists()
        assert (run_dir / "notes.md").exists()
        assert (run_dir / "summary.md").exists()
        assert (tile_dir / "README.md").exists()

        # CSV record appended
        import csv
        rows = list(csv.DictReader((db / "records.csv").read_text(encoding="utf-8").splitlines()))
        assert len(rows) == 1
        assert rows[0]["Tile_ID"] == tile_id
        assert rows[0]["Run_ID"] == "run-001"
    finally:
        shutil.rmtree(tmp)


def test_run_copies_rtl():
    tmp = Path(tempfile.mkdtemp())
    try:
        db = _make_db(tmp)
        _fill_project_config(db)
        from veriflow.commands.create_tile import cmd_create_tile
        cmd_create_tile(db)
        _add_rtl(db, "0001", "my_tile")
        _fill_tile_config(db, "0001", "my_tile")
        _fill_run_config(db, "0001")

        from veriflow.commands.run import cmd_run
        cmd_run(db=db, tile_number="0001", skip_check=True, skip_sim=True, skip_synth=True)

        from veriflow.core.csv_store import get_tile_row
        row = get_tile_row(db / "tile_index.csv", "0001")
        run_dir = db / "tiles" / row["tile_id"] / "runs" / "run-001"
        assert (run_dir / "src" / "rtl" / "my_tile.v").exists()
    finally:
        shutil.rmtree(tmp)


def test_run_multiple_runs():
    tmp = Path(tempfile.mkdtemp())
    try:
        db = _make_db(tmp)
        _fill_project_config(db)
        from veriflow.commands.create_tile import cmd_create_tile
        cmd_create_tile(db)
        _add_rtl(db, "0001", "my_tile")
        _fill_tile_config(db, "0001", "my_tile")
        _fill_run_config(db, "0001")

        from veriflow.commands.run import cmd_run
        cmd_run(db=db, tile_number="0001", skip_check=True, skip_sim=True, skip_synth=True)
        cmd_run(db=db, tile_number="0001", skip_check=True, skip_sim=True, skip_synth=True)

        from veriflow.core.csv_store import get_tile_row
        row = get_tile_row(db / "tile_index.csv", "0001")
        tile_dir = db / "tiles" / row["tile_id"]
        assert (tile_dir / "runs" / "run-001").exists()
        assert (tile_dir / "runs" / "run-002").exists()
    finally:
        shutil.rmtree(tmp)


def test_manifest_custom_serializer():
    """Manifest should contain blank lines between sections."""
    from veriflow.generators.manifest import _render_manifest
    data = {
        "tile_id": "TST-01-26031500010101",
        "run_id": "run-001",
        "date": "2026-03-15",
        "author": "Tester",
        "objective": "Test",
        "status": "PASS",
        "tile": {"tile_name": "T", "top_module": "m", "version": "01", "revision": "01"},
        "tools": {"simulator": "iverilog", "simulator_version": "12.0", "synthesizer": "yosys", "synthesizer_version": ""},
        "run": {"sim_time": "", "seed": ""},
        "sources": {"rtl": ["tiles/x/runs/run-001/src/rtl/m.v"], "tb": []},
        "artifacts": {"connectivity_log": [], "sim_log": [], "synth_log": [], "wave": []},
        "results": {"connectivity": "PASS", "simulation": "SKIPPED", "synthesis": "PASS", "cells": "5", "warnings": "0", "errors": "0"},
    }
    rendered = _render_manifest(data)
    # Must have blank lines between sections
    assert "\n\n" in rendered
    # Must not use yaml.dump formatting
    assert "tile_id:" in rendered
    assert "results:" in rendered


# ── registry ──────────────────────────────────────────────────────────────────

ALL_TESTS = [
    ("tile_id_generation",              test_tile_id_generation),
    ("tile_id_parsing",                 test_tile_id_parsing),
    ("run_id_first",                    test_run_id_first),
    ("run_id_increment",                test_run_id_increment),
    ("init_creates_structure",          test_init_creates_structure),
    ("init_force",                      test_init_force),
    ("init_no_force_raises",            test_init_no_force_raises),
    ("create_tile_structure",           test_create_tile_structure),
    ("create_tile_tiles_dir",           test_create_tile_tiles_dir),
    ("csv_empty_file_rule",             test_csv_empty_file_rule),
    ("csv_header_validation",           test_csv_header_validation),
    ("flat_copy_basic",                 test_flat_copy_basic),
    ("flat_copy_collision",             test_flat_copy_collision),
    ("bump_version",                    test_bump_version),
    ("bump_revision",                   test_bump_revision),
    ("validation_missing_project_config", test_validation_missing_project_config),
    ("validation_empty_id_prefix",      test_validation_empty_id_prefix),
    ("validation_missing_top_module",   test_validation_missing_top_module),
    ("run_creates_structure",           test_run_creates_structure),
    ("run_copies_rtl",                  test_run_copies_rtl),
    ("run_multiple_runs",               test_run_multiple_runs),
    ("manifest_custom_serializer",      test_manifest_custom_serializer),
]

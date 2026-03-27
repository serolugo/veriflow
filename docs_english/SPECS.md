# VeriFlow V1 — System Specification

## 1. Overview

VeriFlow V1 is a lightweight RTL verification framework for multi-project ASIC chip design. It automates the connectivity check, simulation, and synthesis flow for individual hardware tiles, and generates structured documentation for every run.

The system is composed of three internal components orchestrated through a single CLI:

- **VeriTile** — RTL verification engine (connectivity check, simulation, synthesis)
- **AutoDoc** — documentation engine (run records, structured files, CSV indexes)
- **VeriFlow** — CLI orchestrator that coordinates both

---

## 2. Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| External dependencies | PyYAML |
| Persistence | CSV + YAML (no database) |
| Simulator | Icarus Verilog (`iverilog`, `vvp`) |
| Synthesizer | Yosys |
| Waveform viewer | GTKWave |
| Distribution | OSS CAD Suite |
| Compatibility | Windows, Linux, macOS |
| CI/CD | GitHub Actions compatible |

---

## 3. Project Structure

```
veriflow/
├── cli.py                   # CLI entry point
├── commands/                # Per-command implementation
│   ├── init_db.py
│   ├── create_tile.py
│   ├── run.py
│   ├── waves.py
│   ├── bump_version.py
│   └── bump_revision.py
├── core/                    # Reusable core logic
│   ├── __init__.py          # VeriFlowError
│   ├── tile_id.py
│   ├── run_id.py
│   ├── csv_store.py
│   ├── copier.py
│   ├── sim_runner.py
│   ├── synth_runner.py
│   ├── log_parser.py
│   └── validator.py
├── generators/              # Documentation file generators
│   ├── readme.py
│   ├── notes.py
│   ├── manifest.py
│   └── summary.py
├── models/                  # Configuration dataclasses
│   ├── project_config.py
│   ├── tile_config.py
│   └── run_config.py
├── template/                # Base Verilog files (owned by VeriFlow)
│   ├── ip_tile.v
│   ├── tb_base.v
│   ├── tb_tasks.v
│   └── tb_tile_template.v
└── tests/
    ├── runner.py
    └── test_veriflow.py
```

---

## 4. Database Structure

```
database/
├── project_config.yaml       # Global project configuration
├── tile_index.csv            # Index of all tiles
├── records.csv               # Full run history
├── config/
│   └── tile_XXXX/            # User-editable tile configuration
│       ├── tile_config.yaml
│       ├── run_config.yaml
│       └── src/
│           ├── rtl/          # User RTL sources
│           └── tb/           # User test code
└── tiles/
    └── <tile_id>/            # Generated artifacts per tile
        ├── README.md
        ├── works/            # Latest verified sources
│       ├── rtl/
│       └── tb/
        └── runs/
            └── run-NNN/
                ├── manifest.yaml
                ├── notes.md
                ├── summary.md
                ├── src/
                │   ├── rtl/
                │   └── tb/
                └── out/
                    ├── connectivity/logs/
                    ├── sim/logs/ + waves/
                    └── synth/logs/
```

---

## 5. CLI Interface

```bash
python veriflow/cli.py --db <path> <command> [options]
```

| Command | Description |
|---|---|
| `init [--force]` | Initialize the database |
| `create-tile` | Create a new tile |
| `run --tile XXXX [flags]` | Execute the verification pipeline |
| `waves --tile XXXX [--run run-NNN]` | Open GTKWave |
| `bump-version --tile XXXX` | Increment tile version |
| `bump-revision --tile XXXX` | Increment tile revision |

### `run` command flags

| Flag | Description |
|---|---|
| `--skip-check` | Skip connectivity check |
| `--skip-sim` | Skip simulation |
| `--skip-synth` | Skip synthesis |
| `--only-check` | Run connectivity check only |
| `--only-sim` | Run simulation only |
| `--only-synth` | Run synthesis only |
| `--waves` | Launch GTKWave when done |

---

## 6. Tile ID Format

```
<id_prefix>-<YYMMDD><tile_number><id_version><id_revision>
```

Example: `MST130-01-26032500010102`

| Field | Example | Description |
|---|---|---|
| `id_prefix` | `MST130-01` | Defined in `project_config.yaml` |
| `YYMMDD` | `260325` | System date at bump time |
| `tile_number` | `0001` | Unique tile number (4 hex digits) |
| `id_version` | `01` | Internal version (designer iteration) |
| `id_revision` | `02` | Official revision (advisor authorization) |

---

## 7. Version Hierarchy

- **version** — internal increment. The designer uses this to mark development iterations.
- **revision** — major increment. Represents a formal authorization by the advisor.

### Bump behavior

| Command | version | revision | Previous dir | New dir |
|---|---|---|---|---|
| `bump-version` | +1 | unchanged | preserved | created clean |
| `bump-revision` | reset to 01 | +1 | preserved | created clean |

The new directory inherits `works/` from the previous one and starts with an empty `runs/`.

---

## 8. Configuration Files

### `project_config.yaml`
```yaml
id_prefix: ""
project_name: ""
repo: ""
description: |
```

### `tile_config.yaml`
```yaml
tile_name: ""
tile_author: ""
top_module: ""        # must match the RTL module name exactly
description: |
ports: |
usage_guide: |
tb_description: |
```

### `run_config.yaml`
```yaml
run_author: ""
objective: ""
tags: ""
main_change: |
notes: |
```

---

## 9. CSV Files

### `tile_index.csv`
```
tile_number, tile_id, tile_name, tile_author, version, revision
```
- One row per tile
- Updated on every bump
- Source of truth for resolving tile_number → current tile_id

### `records.csv`
```
Tile_ID, Run_ID, Date, Author, Objective, Status,
Version, Revision, Connectivity, Simulation, Synthesis,
Tool_Version, Main_Change, Run_Path, Tags
```
- One row appended per run
- `Run_Path` relative to `tiles/`
- Queryable by an LLM for historical analysis

---

## 10. Verification Pipeline

```
[Connectivity Check] → FAIL → document and stop
        ↓ PASS
[Simulation]         → FAILED → document, continue
        ↓
[Synthesis]          → FAIL → document, complete run
        ↓
[Documentation]      → manifest, notes, summary, README, records
```

### Status derivation

| Condition | Status |
|---|---|
| Connectivity FAIL | FAIL |
| Any stage SKIPPED | PARTIAL |
| All PASS / COMPLETED | PASS |

---

## 11. Testbench Injection

VeriFlow never modifies user files. Instead:

1. Reads `tb_base.v` (owned by VeriFlow)
2. Replaces `/* MODULE_INSTANTIATION */` with the auto-generated DUT instantiation
3. Replaces `/* USER_TEST */` with content extracted from the user test file
4. Writes the result to a temporary file
5. Compiles the temporary file with iverilog
6. Deletes the temporary file when done

The user test file (`src/tb/tb_tile.v`) contains only statements between the markers:
```
// USER TEST STARTS HERE //
...user code...
// USER TEST ENDS HERE //
```

---

## 12. Validation Rules

### Hard errors (stop execution)
- `project_config.yaml` not found
- `tile_index.csv` or `records.csv` not found
- `tiles/` not found
- `tile_config.yaml` or `run_config.yaml` not found
- `src/rtl/` empty or no `.v` files
- `tb_base.v` or `tb_tasks.v` not found in `template/`
- `id_prefix` empty in `project_config.yaml`
- `top_module` empty in `tile_config.yaml`
- No `.v` file whose stem matches `top_module`
- `iverilog` or `yosys` not found in PATH
- Incorrect CSV header in a non-empty file

### Soft errors (continue)
- Empty `tile_index.csv` or `records.csv` → valid, uninitialized
- Optional YAML fields empty → rendered as `""`
- `src/tb/` absent or empty → simulation stage skipped
- Simulation FAILED → document, continue to synthesis
- Synthesis FAIL → document, complete run

---

## 13. Files Generated Per Run

| File | Description |
|---|---|
| `manifest.yaml` | Full run metadata (custom serializer) |
| `notes.md` | Run notes |
| `summary.md` | Tabular results summary |
| `README.md` | Tile documentation (regenerated on every run) |

---

## 14. Tests

Standalone suite at `tests/runner.py`. Does not require pytest.

```bash
python -m veriflow.tests.runner
```

22 integration tests covering:
- Tile ID generation and parsing
- Run ID generation
- init, create-tile, run, bump-version, bump-revision commands
- CSV validation (header, empty file)
- Flat copy with collision resolution
- Validation errors
- Manifest serialization

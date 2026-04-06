# VeriFlow

Lightweight RTL verification and documentation framework for multi-project ASIC chip design. Automates connectivity check, simulation, and synthesis for individual hardware tiles using open-source tooling, and generates structured run records per execution.

---

## Features

- **Two operating modes** — SemiCoLab mode (fixed port convention) and Universal mode (any RTL module)
- **Connectivity check** — verifies port wiring via Icarus Verilog compilation *(SemiCoLab mode)*
- **Simulation** — runs user testbenches and captures VCD waveforms
- **Synthesis** — validates RTL with Yosys, reports cell count, detects inferred latches
- **Auto-documentation** — generates `manifest.yaml`, `summary.md`, `notes.md`, and `README.md` per run
- **Run history** — full CSV records queryable per tile and per run
- **Version tracking** — `bump-version` and `bump-revision` with preserved history
- **GTKWave integration** — open waveforms directly from the CLI

---

## Requirements

- Python 3.10+
- [OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build/releases) (`iverilog`, `vvp`, `yosys`, `gtkwave`)
- PyYAML: `pip install pyyaml`

---

## Quick Start

```bash
# Initialize the database
python veriflow/cli.py --db ./database init

# Set semicolab: true or false in database/project_config.yaml

# Create a tile
python veriflow/cli.py --db ./database create-tile

# Fill in config/tile_0001/ with your RTL and test, then run
python veriflow/cli.py --db ./database run --tile 0001 --waves
```

---

## Operating Modes

Configured via `semicolab` field in `project_config.yaml`. Applies to the entire database.

| Mode | `semicolab` | Connectivity Check | Testbench |
|---|---|---|---|
| SemiCoLab | `true` | ✓ Enabled | Stimuli only — VeriFlow handles the wrapper |
| Universal | `false` | ✗ Skipped | Full testbench — user writes `module tb` |

---

## Commands

```bash
python veriflow/cli.py --db ./database init
python veriflow/cli.py --db ./database create-tile
python veriflow/cli.py --db ./database run --tile 0001 [--waves] [--skip-synth] [--only-check]
python veriflow/cli.py --db ./database waves --tile 0001 [--run run-003]
python veriflow/cli.py --db ./database bump-version --tile 0001
python veriflow/cli.py --db ./database bump-revision --tile 0001
```

---

## Run Summary

```
Tile ID: MST130-01-26032500010101
Tile:    Adder Tile
Run:     run-001
Date:    2026-03-25

| Stage        | Result        | Details          |
|--------------|---------------|------------------|
| Connectivity | PASS          |                  |
| Simulation   | COMPLETED     | 115 ns           |
| Synthesis    | PASS          | 3 cells          |
```

---

## Documentation

| Document | Description |
|---|---|
| [SPECS.md](docs/SPECS.md) | Full system specification |
| [DESIGN.md](docs/DESIGN.md) | Detailed technical design |
| [MANUAL.md](docs/MANUAL.md) | Complete user manual |
| [QUICKREF.md](docs/QUICKREF.md) | Quick reference card |

---

## Tests

```bash
python -m veriflow.tests.runner
# Results: 26 passed, 0 failed
```

---

## Built With

- [Icarus Verilog](http://iverilog.icarus.com/)
- [Yosys](https://yosyshq.net/yosys/)
- [GTKWave](http://gtkwave.sourceforge.net/)
- [OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build)

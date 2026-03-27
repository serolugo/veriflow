# VeriFlow V1

Lightweight RTL verification and documentation framework for multi-project ASIC chip design. Automates connectivity check, simulation, and synthesis for individual hardware tiles using open-source tooling, and generates structured run records per execution.

---

## Features

- **Connectivity check** — verifies port wiring via Icarus Verilog compilation
- **Simulation** — runs user testbenches and captures VCD waveforms
- **Synthesis** — validates RTL with Yosys and reports cell count
- **Auto-documentation** — generates `manifest.yaml`, `summary.md`, `notes.md`, and `README.md` per run
- **Run history** — full CSV records queryable per tile and per run
- **Version tracking** — `bump-version` and `bump-revision` commands with preserved history
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

# Create a tile
python veriflow/cli.py --db ./database create-tile

# Fill in config/tile_0001/ with your RTL and test, then run
python veriflow/cli.py --db ./database run --tile 0001 --waves
```

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
# Results: 22 passed, 0 failed
```

---

## Built With

- [Icarus Verilog](http://iverilog.icarus.com/)
- [Yosys](https://yosyshq.net/yosys/)
- [GTKWave](http://gtkwave.sourceforge.net/)
- [OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build)

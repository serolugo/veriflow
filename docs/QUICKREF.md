# VeriFlow V1 — Quick Reference

## Activate environment (Windows)
```bat
C:\Users\<user>\oss-cad-suite\environment.bat
cd C:\path\to\your\project
```

---

## Commands

```bash
# Initialize database
veriflow --db ./database init
veriflow --db ./database init --force

# Create tile
veriflow --db ./database create-tile

# Full run
veriflow --db ./database run --tile 0001

# Run with options
veriflow --db ./database run --tile 0001 --waves
veriflow --db ./database run --tile 0001 --skip-synth
veriflow --db ./database run --tile 0001 --only-check
veriflow --db ./database run --tile 0001 --skip-sim

# Open waveforms
veriflow --db ./database waves --tile 0001
veriflow --db ./database waves --tile 0001 --run run-003

# Bump version / revision
veriflow --db ./database bump-version --tile 0001
veriflow --db ./database bump-revision --tile 0001

# Run tests
python -m veriflow.tests.runner
```

---

## Operating Modes

Set in `database/project_config.yaml`. Applies to the entire database.

| Field | Description |
|---|---|
| `semicolab: true` | SemiCoLab mode — fixed port convention, connectivity check enabled |
| `semicolab: false` | Universal mode — any RTL module, no connectivity check |

---

## Workflow

```
init → fill project_config.yaml (set semicolab: true or false)
     → create-tile
     → fill tile_config.yaml
     → add RTL to src/rtl/<top_module>.v
     → write test in src/tb/tb_tile.v between the markers
     → update run info in tile_config.yaml
     → run --tile XXXX --waves
```

---

## Files to edit per tile

```
database/config/tile_0001/
├── tile_config.yaml        ← tile info + run info (single file)
└── src/
    ├── rtl/<top_module>.v  ← user RTL
    └── tb/
        ├── tb_tile.v       ← write test here between the markers
        └── tb_tasks.v      ← task library (do not edit, semicolab only)
```

> If no `tb_tile.v` is present, simulation is automatically skipped.

---

## Semicolab testbench (tb_tile.v)

`tb_tile.v` contains the full testbench wrapper. Write your stimuli between the markers only:

```verilog
    // USER TEST STARTS HERE //
    write_data_reg_a(32'd1);
    write_data_reg_b(32'd1);
    @(posedge clk);
    $display("result = %0d", data_reg_c);
    // USER TEST ENDS HERE //
```

VeriFlow extracts the code between the markers and injects it at runtime.
Do not modify the rest of the file (module wrapper, signals, clock, reset, DUT instantiation).

---

## Universal testbench (tb_tile.v)

Write a complete testbench. Top module must be named `tb`:

```verilog
`timescale 1ns / 1ps
module tb;
  // your signals, DUT instantiation and test here
  initial begin
    $finish;
  end
endmodule
```

> `$dumpfile` / `$dumpvars` are injected automatically if not present.

---

## Available tasks (semicolab mode only)

| Task | Description |
|---|---|
| `write_data_reg_a(data)` | Write to data_reg_a |
| `write_data_reg_b(data)` | Write to data_reg_b |
| `write_csr_in(data)` | Write to csr_in |
| `reset_csr_in` | Clear bits [15:12] of csr_in |
| `read_csr_out(data)` | Read csr_out into variable |

**Directly accessible signals:** `clk`, `arst_n`, `csr_in`, `data_reg_a`, `data_reg_b`, `data_reg_c`, `csr_out`, `csr_in_re`, `csr_out_we`

---

## Run status

| Status | Condition |
|---|---|
| `PASS` | All executed stages passed |
| `PARTIAL` | At least one stage was SKIPPED |
| `FAIL` | Connectivity FAIL or Synthesis FAIL |

---

## Tile ID format

```
MST130-01-26032500010102
│         │      │  │  └─ revision (02)
│         │      │  └──── version (01)
│         │      └─────── tile number (0001)
│         └────────────── date YYMMDD (260325)
└──────────────────────── id_prefix
```

---

## Version hierarchy

- `bump-version` → version +1, revision unchanged *(designer iteration)*
- `bump-revision` → revision +1, version reset to 01 *(advisor authorization)*
- Both preserve the previous directory and create a new clean one

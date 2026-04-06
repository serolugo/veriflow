# VeriFlow V1 — Detailed Technical Design

## 1. General Architecture

VeriFlow follows a layered architecture:

```
CLI (cli.py)
    └── Commands (commands/)          ← per-command orchestration
            ├── Core (core/)          ← reusable logic, no UI
            ├── Generators (generators/) ← file generation
            └── Models (models/)      ← configuration dataclasses
```

Communication between layers is unidirectional — commands use core and generators, never the reverse. Errors propagate as `VeriFlowError` and are caught at the CLI entry point.

---

## 2. Module: `cli.py`

**Responsibility:** Entry point. Parses arguments and dispatches to the correct command.

**Implementation:** `argparse` with subcommands. Catches `VeriFlowError` and prints it as `[ERROR]` with exit code 1.

### Path fix
At the top of the file, the package root is inserted into `sys.path` to allow direct execution with `python veriflow/cli.py`:
```python
_pkg_root = Path(__file__).resolve().parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))
```

### Registered subcommands
| Subcommand | Handler |
|---|---|
| `init` | `commands.init_db.cmd_init` |
| `create-tile` | `commands.create_tile.cmd_create_tile` |
| `run` | `commands.run.cmd_run` |
| `waves` | `commands.waves.cmd_waves` |
| `bump-version` | `commands.bump_version.cmd_bump_version` |
| `bump-revision` | `commands.bump_revision.cmd_bump_revision` |

---

## 3. Module: `core/__init__.py`

Defines the base exception:

```python
class VeriFlowError(Exception):
    """Hard error — stops execution and displays [ERROR]."""
```

All errors that must stop the pipeline are raised as `VeriFlowError`. The CLI catches them at the top level.

---

## 4. Module: `core/tile_id.py`

**Responsibility:** Tile ID generation and parsing.

### `generate_tile_id(id_prefix, tile_number, id_version, id_revision, today)`
Builds the Tile ID in the format:
```
<id_prefix>-<YYMMDD><tile_number:04d><id_version:02d><id_revision:02d>
```

### `parse_tile_id(tile_id) → dict`
Decomposes a Tile ID into its parts. Logic assumes the numeric block after the last `-` is exactly 14 characters: 6 (date) + 4 (tile_number) + 2 (version) + 2 (revision).

Returns: `{id_prefix, yymmdd, tile_number, id_version, id_revision}`

---

## 5. Module: `core/run_id.py`

### `get_next_run_id(runs_dir) → str`
Scans `runs_dir` for folders matching `run-NNN`. Returns the next ID with 3-digit zero padding. Returns `"run-001"` if no runs exist.

---

## 6. Module: `core/csv_store.py`

**Responsibility:** Read and write `tile_index.csv` and `records.csv`.

### Expected headers
```python
TILE_INDEX_HEADER = ["tile_number", "tile_id", "tile_name", "tile_author", "version", "revision"]
RECORDS_HEADER    = ["Tile_ID", "Run_ID", "Date", "Author", "Objective", "Status",
                     "Version", "Revision", "Connectivity", "Simulation", "Synthesis",
                     "Tool_Version", "Main_Change", "Run_Path", "Tags"]
```

### Main functions

| Function | Description |
|---|---|
| `read_tile_index(path)` | Reads CSV, validates header |
| `append_tile_index(path, row)` | Appends with auto-header if empty |
| `update_tile_index(path, tile_number, row)` | Replaces the row for the given tile |
| `get_tile_row(path, tile_number)` | Returns row or raises `VeriFlowError` |
| `get_next_tile_number(path)` | Returns the next available number |
| `append_record(path, row)` | Appends to records.csv with auto-header |

### Empty file rule
If a CSV exists but is empty, the header is written before the first append. This allows `init` to create empty files without content.

---

## 7. Module: `core/copier.py`

### `copy_flat(src_dir, dst_dir, extension=".v") → list[Path]`
Copies all files with the given extension from `src_dir` to `dst_dir` in a flat manner (no subdirectory preservation). Resolves name collisions by appending `_1`, `_2`, etc. suffixes.

---

## 8. Module: `core/validator.py`

**Responsibility:** All system validations.

### `validate_database(db)`
Verifies that `project_config.yaml`, `tile_index.csv`, `records.csv`, and `tiles/` exist.

### `validate_tools()`
Verifies that `iverilog` and `yosys` are in PATH using `shutil.which`. Only called when at least one external tool stage will run.

### `validate_run_inputs(db, tile_number_str, tile_config)`
Verifies:
- `config/tile_XXXX/` exists
- `src/rtl/` has `.v` files
- `top_module` is not empty
- A `.v` file whose stem matches `top_module` exists

### `validate_project_config(project_config)`
Verifies that `id_prefix` is not empty.

### `detect_iverilog_version() → str`
Runs `iverilog -V` and parses the version using `log_parser.parse_iverilog_version`.

---

## 9. Module: `core/sim_runner.py`

**Responsibility:** Testbench injection, connectivity check, and simulation.

### Constants
```python
USER_TEST_PLACEHOLDER   = "/* USER_TEST */"
MODULE_INST_PLACEHOLDER = "/* MODULE_INSTANTIATION */"
```

### `_build_dut_inst(top_module) → str`
Generates the DUT instantiation string with the fixed ports from the VeriFlow port convention.

### `_read_user_test(tb_files) → str`
Reads the `src/tb/` files and extracts content between `// USER TEST STARTS HERE //` and `// USER TEST ENDS HERE //` markers. If markers are not present, uses the full file content stripping `timescale`, `module`, and `endmodule`.

### `_inject_tb(tb_base_path, top_module, tb_files) → Path`
1. Reads `tb_base.v`
2. Replaces `MODULE_INST_PLACEHOLDER` with the generated DUT
3. Replaces `USER_TEST_PLACEHOLDER` with user code
4. Writes to a temporary file (`tempfile.NamedTemporaryFile`)
5. Returns the temporary file path

### `run_connectivity_check(...) → str`
Compiles with iverilog using no output file (`/dev/null` or `NUL`). Uses `_inject_tb` without TB files (only verifies DUT connectivity). Returns `"PASS"` or `"FAIL"`.

**Windows fix:** Uses `.as_posix()` on all paths for subprocess calls.

### `run_simulation(...) → tuple[str, dict]`
1. Calls `_inject_tb` with user TB files
2. Compiles into a temp directory without spaces (`tempfile.mkdtemp()`) to avoid Windows path issues
3. Runs `vvp` from `wave_path.parent` so `$dumpfile("waves.vcd")` lands in the correct location
4. Returns `("COMPLETED"|"FAILED", {sim_time, seed})`

### `launch_gtkwave(wave_path)`
Launches GTKWave non-blocking with `subprocess.Popen`.

---

## 10. Module: `core/synth_runner.py`

### `run_synthesis(rtl_files, top_module, synth_log_path) → tuple[str, dict]`
Builds and executes an inline Yosys script:
```
read_verilog <files>
hierarchy -check -top <top_module>
synth
check
stat
```
Returns `("PASS"|"FAIL", {cells, warnings, errors, has_latches})`.

FAIL if: return code != 0 or `"Latch inferred"` detected in the log.

---

## 11. Module: `core/log_parser.py`

### `parse_sim_log(log_text) → dict`
Searches for the iverilog pattern:
```
$finish called at 335000 (1ps)
```
Converts to nanoseconds according to the reported unit. Returns `{sim_time, seed}`.

### `parse_synth_log(log_text) → dict`
Searches for the Yosys stat pattern:
```
      253 cells
```
Takes the last occurrence (final stat block). Returns `{cells, warnings, errors, has_latches}`.

### `parse_iverilog_version(version_output) → str`
Searches for `"Icarus Verilog version X.Y"` in `iverilog -V` output.

---

## 12. Module: `models/`

Three dataclasses with a `from_dict` classmethod that uses `.get()` with default `""` for all fields. All `None` values are normalized to `""`.

### `ProjectConfig`
```python
@dataclass
class ProjectConfig:
    id_prefix: str
    project_name: str
    repo: str
    description: str
    semicolab: bool = True  # True = SemiCoLab mode, False = Universal mode
```

The `semicolab` field defaults to `True`. Accepts `true`/`false` in YAML. Parsed via `from_dict` which normalizes string values (`"false"`, `"0"`, `"no"` → `False`).

### `TileConfig`
```python
@dataclass
class TileConfig:
    tile_name: str
    tile_author: str
    top_module: str
    description: str
    ports: str
    usage_guide: str
    tb_description: str
```

### `RunConfig`
```python
@dataclass
class RunConfig:
    run_author: str
    objective: str
    tags: str
    main_change: str
    notes: str
```

---

## 13. Module: `generators/readme.py`

### `generate_readme(tile_id, tile_config, output_path)`
Generates `README.md` with fields from `tile_config`. Called in `create-tile` (with empty config) and regenerated on every `run` with updated config.

---

## 14. Module: `generators/notes.py`

### `generate_notes(tile_id, tile_config, run_config, output_path)`
Generates `notes.md` with the `notes` field from `run_config`. Generated once per run.

---

## 15. Module: `generators/manifest.py`

### `generate_manifest(data, output_path)`
Wrapper over `_render_manifest`.

### `_render_manifest(data) → str`
Custom serializer — **does not use `yaml.dump`**. Generates YAML manually inserting blank lines between logical sections for readability. All values are wrapped in double quotes. Empty lists render as `[]`, non-empty as items with `- "value"`.

Manifest sections:
1. Identity (tile_id, run_id, date, author)
2. Objective and status
3. Tile info (tile_name, top_module, version, revision)
4. Tools (simulator, synthesizer + versions)
5. Run params (sim_time, seed)
6. Sources (rtl[], tb[])
7. Artifacts (logs[], waves[])
8. Results (connectivity, simulation, synthesis, cells, warnings, errors)

---

## 16. Module: `generators/summary.py`

### `generate_summary(...) → str`
Generates `summary.md` with a results table and also prints it to the console. Returns the string so `cmd_run` can print it.

Table format:
```
| Stage        | Result        | Details          |
|--------------|---------------|------------------|
| Connectivity | PASS          |                  |
| Simulation   | COMPLETED     | 335 ns           |
| Synthesis    | PASS          | 253 cells        |
```

---

## 17. Commands

### `cmd_init(db, force)`
Creates the full database structure. With `--force` overwrites if it already exists. Creates `.gitkeep` in `tiles/`.

### `cmd_create_tile(db)`
1. Reads `id_prefix` from `project_config.yaml`
2. Calculates next `tile_number`
3. Generates `tile_id` with version=01, revision=01
4. Creates `config/tile_XXXX/` with YAML templates
5. Creates `src/rtl/` and `src/tb/` (with `tb_tile_template.v`)
6. Creates `tiles/<tile_id>/` with README, works/, runs/
7. Appends to `tile_index.csv`

### `cmd_run(db, tile_number, skip_*, only_*, waves)`
Main pipeline. `--only-*` flags are internally translated to `skip_*` combinations. `validate_tools()` is only called if at least one tool stage will run. See Pipeline section in SPECS.md.

### `cmd_waves(db, tile_number, run_id)`
Resolves run ID (latest if not specified), verifies `waves.vcd` exists, and launches GTKWave with `subprocess.Popen` (non-blocking).

### `cmd_bump_version(db, tile_number)`
- Increments version, revision unchanged
- Preserves previous directory
- Creates new directory with works/ copied and clean runs/

### `cmd_bump_revision(db, tile_number)`
- Increments revision, version **reset to 01**
- Preserves previous directory
- Creates new directory with works/ copied and clean runs/

---

## 18. Verilog Templates

### `ip_tile.v`
Base RTL template for the user. Defines VeriFlow's fixed port convention. The user implements logic between `// USER LOGIC STARTS HERE //` and `// USER LOGIC ENDS HERE //`.

### `tb_base.v`
Base testbench. **Owned by VeriFlow — the user never edits it.** Contains two runtime-injected placeholders:
- `/* MODULE_INSTANTIATION */` — replaced with DUT instantiation
- `/* USER_TEST */` — replaced with user test code

### `tb_tasks.v`
Task library included inside the `tb` module via `` `include "tb_tasks.v" `` (after signal declarations). Provides: `write_data_reg_a`, `write_data_reg_b`, `write_csr_in`, `reset_csr_in`, `read_csr_out`.

### `tb_tile_template.v`
User-facing test template. Copied to `config/tile_XXXX/src/tb/tb_tile.v` on `create-tile`. The user writes tests between the `// USER TEST STARTS HERE //` and `// USER TEST ENDS HERE //` markers.

---

## 19. Fixed Port Convention

All VeriFlow tiles implement exactly these ports:

| Port | Direction | Width | Description |
|---|---|---|---|
| `clk` | input | 1 | Clock |
| `arst_n` | input | 1 | Async reset, active low |
| `csr_in` | input | 16 | Control/Status Register input |
| `data_reg_a` | input | 32 | Operand A |
| `data_reg_b` | input | 32 | Operand B |
| `data_reg_c` | output | 32 | Result |
| `csr_out` | output | 16 | Control/Status Register output |
| `csr_in_re` | output | 1 | CSR input read enable |
| `csr_out_we` | output | 1 | CSR output write enable |

---

## 20. Windows Compatibility Notes

- All paths use `pathlib.Path`
- Subprocess calls use `.as_posix()` on paths
- Simulation compilation uses `tempfile.mkdtemp()` to avoid paths with spaces
- `vvp` is run with the compiled binary via posix path
- Connectivity check uses `"NUL"` as output on Windows

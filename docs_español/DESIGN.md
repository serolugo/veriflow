# VeriFlow V1 — Diseño Técnico Detallado

## 1. Arquitectura General

VeriFlow sigue una arquitectura de capas:

```
CLI (cli.py)
    └── Commands (commands/)        ← orquestación de cada comando
            ├── Core (core/)        ← lógica reutilizable, sin UI
            ├── Generators (generators/) ← generación de archivos
            └── Models (models/)    ← dataclasses de configuración
```

La comunicación entre capas es unidireccional — los commands usan core y generators, nunca al revés. Los errores se propagan como `VeriFlowError` y son capturados en el entry point del CLI.

---

## 2. Módulo: `cli.py`

**Responsabilidad:** Entry point. Parsea argumentos y despacha al comando correcto.

**Implementación:** `argparse` con subcomandos. Captura `VeriFlowError` y la imprime como `[ERROR]` con exit code 1.

### Path fix
Al inicio del archivo se inserta el directorio raíz del paquete en `sys.path` para permitir ejecución directa con `python veriflow/cli.py`:
```python
_pkg_root = Path(__file__).resolve().parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))
```

### Subcomandos registrados
| Subcomando | Handler |
|---|---|
| `init` | `commands.init_db.cmd_init` |
| `create-tile` | `commands.create_tile.cmd_create_tile` |
| `run` | `commands.run.cmd_run` |
| `waves` | `commands.waves.cmd_waves` |
| `bump-version` | `commands.bump_version.cmd_bump_version` |
| `bump-revision` | `commands.bump_revision.cmd_bump_revision` |

---

## 3. Módulo: `core/__init__.py`

Define la excepción base del sistema:

```python
class VeriFlowError(Exception):
    """Error duro — detiene ejecución y muestra [ERROR]."""
```

Todos los errores que deben detener el pipeline se lanzan como `VeriFlowError`. El CLI los captura en el top level.

---

## 4. Módulo: `core/tile_id.py`

**Responsabilidad:** Generación y parsing del Tile ID.

### `generate_tile_id(id_prefix, tile_number, id_version, id_revision, today)`
Construye el Tile ID en formato:
```
<id_prefix>-<YYMMDD><tile_number:04d><id_version:02d><id_revision:02d>
```

### `parse_tile_id(tile_id) → dict`
Descompone un Tile ID en sus partes. La lógica asume que el bloque numérico después del último `-` tiene exactamente 14 caracteres: 6 (fecha) + 4 (tile_number) + 2 (version) + 2 (revision).

Retorna: `{id_prefix, yymmdd, tile_number, id_version, id_revision}`

---

## 5. Módulo: `core/run_id.py`

### `get_next_run_id(runs_dir) → str`
Escanea `runs_dir` buscando carpetas con formato `run-NNN`. Retorna el siguiente ID con padding de 3 dígitos. Si no hay runs existentes retorna `"run-001"`.

---

## 6. Módulo: `core/csv_store.py`

**Responsabilidad:** Lectura y escritura de `tile_index.csv` y `records.csv`.

### Headers esperados
```python
TILE_INDEX_HEADER = ["tile_number", "tile_id", "tile_name", "tile_author", "version", "revision"]
RECORDS_HEADER    = ["Tile_ID", "Run_ID", "Date", "Author", "Objective", "Status",
                     "Version", "Revision", "Connectivity", "Simulation", "Synthesis",
                     "Tool_Version", "Main_Change", "Run_Path", "Tags"]
```

### Funciones principales

| Función | Descripción |
|---|---|
| `read_tile_index(path)` | Lee el CSV, valida header |
| `append_tile_index(path, row)` | Append con auto-header si vacío |
| `update_tile_index(path, tile_number, row)` | Reemplaza la fila del tile |
| `get_tile_row(path, tile_number)` | Retorna la fila o lanza `VeriFlowError` |
| `get_next_tile_number(path)` | Retorna el siguiente número disponible |
| `append_record(path, row)` | Append a records.csv con auto-header |

### Regla de archivo vacío
Si un CSV existe pero está vacío, se escribe el header antes del primer append. Esto permite que `init` cree archivos vacíos sin contenido.

---

## 7. Módulo: `core/copier.py`

### `copy_flat(src_dir, dst_dir, extension=".v") → list[Path]`
Copia todos los archivos con la extensión dada de `src_dir` a `dst_dir` de forma plana (sin preservar subdirectorios). Resuelve colisiones de nombre agregando sufijos `_1`, `_2`, etc.

---

## 8. Módulo: `core/validator.py`

**Responsabilidad:** Todas las validaciones del sistema.

### `validate_database(db)`
Verifica que existan `project_config.yaml`, `tile_index.csv`, `records.csv` y `tiles/`.

### `validate_tools()`
Verifica que `iverilog` y `yosys` estén en PATH usando `shutil.which`. Solo se llama cuando al menos un stage de herramienta externas va a correr.

### `validate_run_inputs(db, tile_number_str, tile_config)`
Verifica:
- Que exista `config/tile_XXXX/`
- Que `src/rtl/` tenga archivos `.v`
- Que `top_module` no esté vacío
- Que exista un `.v` cuyo stem coincida con `top_module`

### `validate_project_config(project_config)`
Verifica que `id_prefix` no esté vacío.

### `detect_iverilog_version() → str`
Ejecuta `iverilog -V` y parsea la versión con `log_parser.parse_iverilog_version`.

---

## 9. Módulo: `core/sim_runner.py`

**Responsabilidad:** Inyección del TB, connectivity check y simulación.

### Constantes
```python
USER_TEST_PLACEHOLDER  = "/* USER_TEST */"
MODULE_INST_PLACEHOLDER = "/* MODULE_INSTANTIATION */"
```

### `_build_dut_inst(top_module) → str`
Genera el string de instanciación del DUT con los puertos fijos del port convention de VeriFlow.

### `_read_user_test(tb_files) → str`
Lee los archivos de `src/tb/` y extrae el contenido entre los marcadores `// USER TEST STARTS HERE //` y `// USER TEST ENDS HERE //`. Si los marcadores no están presentes, usa el archivo completo strippeando `timescale`, `module` y `endmodule`.

### `_inject_tb(tb_base_path, top_module, tb_files) → Path`
1. Lee `tb_base.v`
2. Reemplaza `MODULE_INST_PLACEHOLDER` con el DUT generado
3. Reemplaza `USER_TEST_PLACEHOLDER` con el código del usuario
4. Escribe en un archivo temporal (`tempfile.NamedTemporaryFile`)
5. Retorna el path del temporal

### `run_connectivity_check(...) → str`
Compila con iverilog sin archivo de output (`/dev/null` o `NUL`). Usa `_inject_tb` sin TB files (solo verifica conectividad del DUT). Retorna `"PASS"` o `"FAIL"`.

**Fix Windows:** Usa `.as_posix()` en todos los paths para subprocess calls.

### `run_simulation(...) → tuple[str, dict]`
1. Llama `_inject_tb` con los TB files del usuario
2. Compila en un directorio temporal sin espacios (`tempfile.mkdtemp()`) para evitar problemas con paths de Windows
3. Ejecuta `vvp` desde `wave_path.parent` para que `$dumpfile("waves.vcd")` aterrice en el lugar correcto
4. Retorna `("COMPLETED"|"FAILED", {sim_time, seed})`

### `launch_gtkwave(wave_path)`
Lanza GTKWave de forma no bloqueante con `subprocess.Popen`.

---

## 10. Módulo: `core/synth_runner.py`

### `run_synthesis(rtl_files, top_module, synth_log_path) → tuple[str, dict]`
Construye y ejecuta un script Yosys inline:
```
read_verilog <files>
hierarchy -check -top <top_module>
synth
check
stat
```
Retorna `("PASS"|"FAIL", {cells, warnings, errors, has_latches})`.

FAIL si: return code != 0 o se detecta `"Latch inferred"` en el log.

---

## 11. Módulo: `core/log_parser.py`

### `parse_sim_log(log_text) → dict`
Busca el patrón de iverilog:
```
$finish called at 335000 (1ps)
```
Convierte a nanosegundos según la unidad reportada. Retorna `{sim_time, seed}`.

### `parse_synth_log(log_text) → dict`
Busca el patrón de Yosys stat:
```
      253 cells
```
Toma la última ocurrencia (bloque final de stat). Retorna `{cells, warnings, errors, has_latches}`.

### `parse_iverilog_version(version_output) → str`
Busca `"Icarus Verilog version X.Y"` en la salida de `iverilog -V`.

---

## 12. Módulo: `models/`

Tres dataclasses con método `from_dict` que usa `.get()` con default `""` para todos los campos. Todos los valores `None` se normalizan a `""`.

### `ProjectConfig`
```python
@dataclass
class ProjectConfig:
    id_prefix: str
    project_name: str
    repo: str
    description: str
```

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

## 13. Módulo: `generators/readme.py`

### `generate_readme(tile_id, tile_config, output_path)`
Genera `README.md` con los campos de `tile_config`. Se llama en `create-tile` (con config vacía) y se regenera en cada `run` con la config actualizada.

---

## 14. Módulo: `generators/notes.py`

### `generate_notes(tile_id, tile_config, run_config, output_path)`
Genera `notes.md` con el campo `notes` de `run_config`. Se genera una vez por run.

---

## 15. Módulo: `generators/manifest.py`

### `generate_manifest(data, output_path)`
Wrapper sobre `_render_manifest`.

### `_render_manifest(data) → str`
Serializer custom — **no usa `yaml.dump`**. Genera el YAML manualmente insertando líneas en blanco entre secciones lógicas para legibilidad. Todos los valores se envuelven en comillas dobles. Las listas vacías se renderizan como `[]`, las no vacías como items con `- "valor"`.

Secciones del manifest:
1. Identidad (tile_id, run_id, date, author)
2. Objetivo y status
3. Tile info (tile_name, top_module, version, revision)
4. Tools (simulator, synthesizer + versiones)
5. Run params (sim_time, seed)
6. Sources (rtl[], tb[])
7. Artifacts (logs[], waves[])
8. Results (connectivity, simulation, synthesis, cells, warnings, errors)

---

## 16. Módulo: `generators/summary.py`

### `generate_summary(...) → str`
Genera `summary.md` con tabla de resultados y lo imprime también en consola. Retorna el string para que `cmd_run` lo imprima.

Formato de la tabla:
```
| Stage        | Result        | Details          |
|--------------|---------------|------------------|
| Connectivity | PASS          |                  |
| Simulation   | COMPLETED     | 335 ns           |
| Synthesis    | PASS          | 253 cells        |
```

---

## 17. Comandos

### `cmd_init(db, force)`
Crea la estructura completa de la base de datos. Con `--force` sobreescribe si ya existe. Crea `.gitkeep` en `tiles/`.

### `cmd_create_tile(db)`
1. Lee `id_prefix` de `project_config.yaml`
2. Calcula siguiente `tile_number`
3. Genera `tile_id` con version=01, revision=01
4. Crea `config/tile_XXXX/` con templates de yaml
5. Crea `src/rtl/` y `src/tb/` (con `tb_tile_template.v`)
6. Crea `tiles/<tile_id>/` con README, works/, runs/
7. Append a `tile_index.csv`

### `cmd_run(db, tile_number, skip_*, only_*, waves)`
Pipeline principal. Los flags `--only-*` se traducen internamente a combinaciones de `skip_*`. `validate_tools()` solo se llama si al menos un stage de herramienta va a correr. Ver sección de Pipeline en SPECS.md.

### `cmd_waves(db, tile_number, run_id)`
Resuelve el run ID (último si no se especifica), verifica que exista `waves.vcd` y lanza GTKWave con `subprocess.Popen` (no bloqueante).

### `cmd_bump_version(db, tile_number)`
- Incrementa version, revisión sin cambio
- Preserva dir anterior
- Crea dir nuevo con works/ copiado y runs/ limpio

### `cmd_bump_revision(db, tile_number)`
- Incrementa revisión, version **reset a 01**
- Preserva dir anterior
- Crea dir nuevo con works/ copiado y runs/ limpio

---

## 18. Templates Verilog

### `ip_tile.v`
Plantilla RTL base para el usuario. Define el port convention fijo de VeriFlow. El usuario implementa lógica entre `// USER LOGIC STARTS HERE //` y `// USER LOGIC ENDS HERE //`.

### `tb_base.v`
Testbench base. **Propiedad de VeriFlow — el usuario nunca lo edita.** Contiene dos placeholders inyectados en tiempo de ejecución:
- `/* MODULE_INSTANTIATION */` — reemplazado con la instanciación del DUT
- `/* USER_TEST */` — reemplazado con el código de test del usuario

### `tb_tasks.v`
Librería de tasks incluida dentro del módulo `tb` vía `` `include "tb_tasks.v" `` (después de las declaraciones de señales). Provee: `write_data_reg_a`, `write_data_reg_b`, `write_csr_in`, `reset_csr_in`, `read_csr_out`.

### `tb_tile_template.v`
Plantilla de test para el usuario. Se copia a `config/tile_XXXX/src/tb/tb_tile.v` al hacer `create-tile`. El usuario escribe sus tests entre los marcadores `// USER TEST STARTS HERE //` y `// USER TEST ENDS HERE //`.

---

## 19. Port Convention Fijo

Todos los tiles de VeriFlow implementan exactamente estos puertos:

| Puerto | Dirección | Ancho | Descripción |
|---|---|---|---|
| `clk` | input | 1 | Clock |
| `arst_n` | input | 1 | Reset asíncrono, activo en bajo |
| `csr_in` | input | 16 | Control/Status Register entrada |
| `data_reg_a` | input | 32 | Operando A |
| `data_reg_b` | input | 32 | Operando B |
| `data_reg_c` | output | 32 | Resultado |
| `csr_out` | output | 16 | Control/Status Register salida |
| `csr_in_re` | output | 1 | Read enable de CSR entrada |
| `csr_out_we` | output | 1 | Write enable de CSR salida |

---

## 20. Consideraciones de Compatibilidad Windows

- Todos los paths usan `pathlib.Path`
- Subprocess calls usan `.as_posix()` en paths
- La compilación de simulación usa `tempfile.mkdtemp()` para evitar paths con espacios
- `vvp` se ejecuta con el binario compilado via path posix
- El connectivity check usa `"NUL"` como output en Windows

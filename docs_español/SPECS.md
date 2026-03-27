# VeriFlow V1 — Especificación del Sistema

## 1. Descripción General

VeriFlow V1 es un framework de verificación RTL ligero para diseño de chips ASIC multi-proyecto. Automatiza el flujo de connectivity check, simulación y síntesis sobre tiles de hardware individuales, y genera documentación estructurada por cada ejecución.

El sistema está compuesto por tres componentes internos que se orquestan a través de una única CLI:

- **VeriTile** — motor de verificación RTL (connectivity check, simulación, síntesis)
- **AutoDoc** — motor de documentación (registros de runs, archivos estructurados, índices CSV)
- **VeriFlow** — orquestador CLI que coordina ambos

---

## 2. Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.10+ |
| Dependencias externas | PyYAML |
| Persistencia | CSV + YAML (sin base de datos) |
| Simulator | Icarus Verilog (`iverilog`, `vvp`) |
| Synthesizer | Yosys |
| Waveform viewer | GTKWave |
| Distribución | OSS CAD Suite |
| Compatibilidad | Windows, Linux, macOS |
| CI/CD | Compatible con GitHub Actions |

---

## 3. Estructura del Proyecto

```
veriflow/
├── cli.py                   # Punto de entrada CLI
├── commands/                # Implementación de cada subcomando
│   ├── init_db.py
│   ├── create_tile.py
│   ├── run.py
│   ├── waves.py
│   ├── bump_version.py
│   └── bump_revision.py
├── core/                    # Lógica central reutilizable
│   ├── __init__.py          # VeriFlowError
│   ├── tile_id.py
│   ├── run_id.py
│   ├── csv_store.py
│   ├── copier.py
│   ├── sim_runner.py
│   ├── synth_runner.py
│   ├── log_parser.py
│   └── validator.py
├── generators/              # Generadores de archivos de documentación
│   ├── readme.py
│   ├── notes.py
│   ├── manifest.py
│   └── summary.py
├── models/                  # Dataclasses de configuración
│   ├── project_config.py
│   ├── tile_config.py
│   └── run_config.py
├── template/                # Archivos Verilog base (propiedad de VeriFlow)
│   ├── ip_tile.v
│   ├── tb_base.v
│   ├── tb_tasks.v
│   └── tb_tile_template.v
└── tests/
    ├── runner.py
    └── test_veriflow.py
```

---

## 4. Estructura de la Base de Datos

```
database/
├── project_config.yaml       # Configuración global del proyecto
├── tile_index.csv            # Índice de todos los tiles
├── records.csv               # Historial de todos los runs
├── config/
│   └── tile_XXXX/            # Configuración editable por tile
│       ├── tile_config.yaml
│       ├── run_config.yaml
│       └── src/
│           ├── rtl/          # Fuentes RTL del usuario
│           └── tb/           # Código de test del usuario
└── tiles/
    └── <tile_id>/            # Artefactos generados por tile
        ├── README.md
        ├── works/            # Última versión de fuentes verificadas
        │   ├── rtl/
        │   └── tb/
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

## 5. Interfaz CLI

```bash
python veriflow/cli.py --db <path> <comando> [opciones]
```

| Comando | Descripción |
|---|---|
| `init [--force]` | Inicializa la base de datos |
| `create-tile` | Crea un nuevo tile |
| `run --tile XXXX [flags]` | Ejecuta el pipeline de verificación |
| `waves --tile XXXX [--run run-NNN]` | Abre GTKWave |
| `bump-version --tile XXXX` | Incrementa versión del tile |
| `bump-revision --tile XXXX` | Incrementa revisión del tile |

### Flags del comando `run`

| Flag | Descripción |
|---|---|
| `--skip-check` | Omite connectivity check |
| `--skip-sim` | Omite simulación |
| `--skip-synth` | Omite síntesis |
| `--only-check` | Solo connectivity check |
| `--only-sim` | Solo simulación |
| `--only-synth` | Solo síntesis |
| `--waves` | Lanza GTKWave al terminar |

---

## 6. Formato del Tile ID

```
<id_prefix>-<YYMMDD><tile_number><id_version><id_revision>
```

Ejemplo: `MST130-01-26032500010102`

| Campo | Ejemplo | Descripción |
|---|---|---|
| `id_prefix` | `MST130-01` | Definido en `project_config.yaml` |
| `YYMMDD` | `260325` | Fecha del sistema al momento del bump |
| `tile_number` | `0001` | Número único del tile (4 hex dígitos) |
| `id_version` | `01` | Versión interna (cambio del diseñador) |
| `id_revision` | `02` | Revisión oficial (autorización del asesor) |

---

## 7. Jerarquía de Versiones

- **version** — incremento interno. El diseñador lo usa para marcar iteraciones de desarrollo.
- **revision** — incremento mayor. Representa una autorización formal del asesor.

### Comportamiento de bump

| Comando | version | revision | Dir anterior | Dir nuevo |
|---|---|---|---|---|
| `bump-version` | +1 | sin cambio | preservado | creado limpio |
| `bump-revision` | reset a 01 | +1 | preservado | creado limpio |

El directorio nuevo hereda `works/` del anterior y arranca con `runs/` vacío.

---

## 8. Archivos de Configuración

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
top_module: ""        # debe coincidir con el nombre del módulo RTL
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

## 9. Archivos CSV

### `tile_index.csv`
```
tile_number, tile_id, tile_name, tile_author, version, revision
```
- Una fila por tile
- Se actualiza en cada bump
- Fuente de verdad para resolver tile_number → tile_id actual

### `records.csv`
```
Tile_ID, Run_ID, Date, Author, Objective, Status,
Version, Revision, Connectivity, Simulation, Synthesis,
Tool_Version, Main_Change, Run_Path, Tags
```
- Una fila appended por run
- `Run_Path` relativo a `tiles/`
- Consultable por un LLM para análisis histórico

---

## 10. Pipeline de Verificación

```
[Connectivity Check] → FAIL → documenta y termina
        ↓ PASS
[Simulation]         → FAILED → documenta, continúa
        ↓
[Synthesis]          → FAIL → documenta, completa run
        ↓
[Documentación]      → manifest, notes, summary, README, records
```

### Derivación de Status

| Condición | Status |
|---|---|
| Connectivity FAIL | FAIL |
| Algún stage SKIPPED | PARTIAL |
| Todo PASS / COMPLETED | PASS |

---

## 11. Inyección del Testbench

VeriFlow nunca modifica los archivos del usuario. En su lugar:

1. Lee `tb_base.v` (propiedad de VeriFlow)
2. Reemplaza `/* MODULE_INSTANTIATION */` con la instanciación del DUT generada automáticamente
3. Reemplaza `/* USER_TEST */` con el contenido extraído del archivo de test del usuario
4. Escribe el resultado en un archivo temporal
5. Compila el archivo temporal con iverilog
6. Elimina el temporal al terminar

El archivo de test del usuario (`src/tb/tb_tile.v`) solo contiene statements entre los marcadores:
```
// USER TEST STARTS HERE //
...código del usuario...
// USER TEST ENDS HERE //
```

---

## 12. Reglas de Validación

### Errores duros (detienen ejecución)
- `project_config.yaml` no encontrado
- `tile_index.csv` o `records.csv` no encontrado
- `tiles/` no encontrado
- `tile_config.yaml` o `run_config.yaml` no encontrado
- `src/rtl/` vacío o sin archivos `.v`
- `tb_base.v` o `tb_tasks.v` no encontrado en template/
- `id_prefix` vacío en `project_config.yaml`
- `top_module` vacío en `tile_config.yaml`
- No existe `.v` cuyo stem coincida con `top_module`
- `iverilog` o `yosys` no encontrado en PATH
- Header CSV incorrecto en archivo no vacío

### Errores suaves (continúan)
- `tile_index.csv` o `records.csv` vacíos → válido, sin inicializar
- Campos YAML opcionales vacíos → se renderizan como `""`
- `src/tb/` ausente o vacío → simulación se omite
- Simulation FAILED → documenta, continúa a síntesis
- Synthesis FAIL → documenta, completa run

---

## 13. Archivos Generados por Run

| Archivo | Descripción |
|---|---|
| `manifest.yaml` | Metadata completa del run (custom serializer) |
| `notes.md` | Notas del run |
| `summary.md` | Resumen tabular con resultados |
| `README.md` | Documentación del tile (regenerado en cada run) |

---

## 14. Tests

Suite standalone en `tests/runner.py`. No requiere pytest.

```bash
python -m veriflow.tests.runner
```

22 tests de integración cubriendo:
- Generación y parsing de Tile ID
- Generación de Run ID
- Comandos init, create-tile, run, bump-version, bump-revision
- Validación de CSV (header, archivo vacío)
- Copia flat con resolución de colisiones
- Errores de validación
- Serialización del manifest

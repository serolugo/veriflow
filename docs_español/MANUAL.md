# VeriFlow V1 — Manual de Usuario

## 1. Introducción

VeriFlow V1 es un framework de verificación RTL diseñado para el flujo de diseño de chips ASIC multi-proyecto. Automatiza tres etapas de verificación — connectivity check, simulación y síntesis — y genera documentación estructurada por cada ejecución.

**Componentes internos:**
- **VeriTile** — motor de verificación (iverilog + Yosys)
- **AutoDoc** — motor de documentación (YAML, CSV, Markdown)
- **VeriFlow** — orquestador CLI

---

## 2. Requisitos

- Python 3.10 o superior
- PyYAML: `pip install pyyaml`
- [OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build/releases) con `iverilog`, `vvp`, `yosys` y `gtkwave` en PATH

### Verificar instalación
```bash
iverilog -V
yosys --version
```

---

## 3. Instalación

Extrae el zip en tu proyecto. La estructura debe quedar:

```
tu_proyecto/
└── veriflow/
    ├── cli.py
    ├── commands/
    ├── core/
    ├── generators/
    ├── models/
    ├── template/
    └── tests/
```

Verifica que todo funciona:
```bash
python -m veriflow.tests.runner
```

Resultado esperado: `22 passed, 0 failed`.

---

## 4. Inicialización del Proyecto

### 4.1 Crear la base de datos

```bash
python veriflow/cli.py --db ./database init
```

Esto crea:
```
database/
├── project_config.yaml
├── tile_index.csv
├── records.csv
├── config/
└── tiles/
```

Si la carpeta ya existe, usa `--force` para sobreescribir:
```bash
python veriflow/cli.py --db ./database init --force
```

### 4.2 Configurar el proyecto

Edita `database/project_config.yaml`:

```yaml
id_prefix: "MST130-01"       # prefijo para los Tile IDs
project_name: "Mi Chip"
repo: "https://github.com/usuario/repo"
description: |
  Descripción del proyecto de chip.
```

El campo `id_prefix` es obligatorio — sin él no se pueden crear tiles.

---

## 5. Gestión de Tiles

### 5.1 Crear un tile

```bash
python veriflow/cli.py --db ./database create-tile
```

Genera automáticamente:
- `database/config/tile_0001/tile_config.yaml` — configuración del tile
- `database/config/tile_0001/run_config.yaml` — configuración del run
- `database/config/tile_0001/src/rtl/` — carpeta para el RTL
- `database/config/tile_0001/src/tb/tb_tile.v` — plantilla de test
- `database/tiles/<tile_id>/` — directorio de artefactos

### 5.2 Configurar el tile

**`tile_config.yaml`** — llenar antes del primer run:
```yaml
tile_name: "Adder Tile"
tile_author: "Sebastian"
top_module: "adder_tile"    # nombre exacto del módulo RTL
description: |
  Tile sumador de 32 bits.
ports: |
  data_reg_a, data_reg_b: operandos
  data_reg_c: resultado
usage_guide: |
  Conectar operandos, leer resultado en data_reg_c.
tb_description: |
  Prueba sumas básicas y overflow.
```

> El campo `top_module` debe coincidir exactamente con el nombre del archivo `.v` en `src/rtl/`.

### 5.3 Agregar el RTL

Crea `database/config/tile_0001/src/rtl/adder_tile.v`:

```verilog
`timescale 1ns / 1ps

module adder_tile #(
    parameter REG_WIDTH     = 32,
    parameter CSR_IN_WIDTH  = 16,
    parameter CSR_OUT_WIDTH = 16
)(
    input  wire                      clk,
    input  wire                      arst_n,
    input  wire [CSR_IN_WIDTH-1:0]   csr_in,
    input  wire [REG_WIDTH-1:0]      data_reg_a,
    input  wire [REG_WIDTH-1:0]      data_reg_b,
    output wire [REG_WIDTH-1:0]      data_reg_c,
    output wire [CSR_OUT_WIDTH-1:0]  csr_out,
    output wire                      csr_in_re,
    output wire                      csr_out_we
);

    // USER LOGIC STARTS HERE //
    assign data_reg_c = data_reg_a + data_reg_b;
    assign csr_out    = 16'b0;
    assign csr_in_re  = 1'b0;
    assign csr_out_we = 1'b0;
    // USER LOGIC ENDS HERE //

endmodule
```

> Todos los tiles deben implementar exactamente los 9 puertos del port convention de VeriFlow.

### 5.4 Escribir el testbench

Edita `database/config/tile_0001/src/tb/tb_tile.v`. Solo escribe código entre los marcadores:

```verilog
// USER TEST STARTS HERE //
write_data_reg_a(32'd10);
write_data_reg_b(32'd20);
@(posedge clk);
$display("resultado = %0d", data_reg_c);  // esperado: 30
// USER TEST ENDS HERE //
```

**Tasks disponibles:**

| Task | Uso |
|---|---|
| `write_data_reg_a(data)` | Aplica valor a data_reg_a en el siguiente posedge |
| `write_data_reg_b(data)` | Aplica valor a data_reg_b en el siguiente posedge |
| `write_csr_in(data)` | Aplica valor a csr_in |
| `reset_csr_in` | Limpia bits [15:12] de csr_in |
| `read_csr_out(data)` | Captura csr_out en variable |

**Señales accesibles directamente:**
`clk`, `arst_n`, `csr_in`, `data_reg_a`, `data_reg_b`, `data_reg_c`, `csr_out`, `csr_in_re`, `csr_out_we`

> El testbench incluye automáticamente 2 ciclos de reset al inicio antes de llamar tu código.

### 5.5 Configurar el run

Edita `database/config/tile_0001/run_config.yaml` antes de cada run:

```yaml
run_author: "Sebastian"
objective: "Verificación inicial del sumador"
tags: "initial, adder"
main_change: |
  Implementación inicial del sumador de 32 bits.
notes: |
  Sin notas adicionales.
```

---

## 6. Ejecución del Pipeline

### 6.1 Run completo

```bash
python veriflow/cli.py --db ./database run --tile 0001
```

El pipeline ejecuta en orden:

1. **Connectivity check** — compila RTL + TB con iverilog para verificar que los puertos conectan correctamente. Si falla, el pipeline se detiene.
2. **Simulation** — compila e inyecta el test del usuario, ejecuta con `vvp`, genera `waves.vcd`.
3. **Synthesis** — corre Yosys con hierarchy check, synth, check y stat.
4. **Documentación** — genera manifest, notes, summary, README, actualiza records.csv.

### 6.2 Opciones del run

```bash
# Ver waveforms automáticamente al terminar
python veriflow/cli.py --db ./database run --tile 0001 --waves

# Solo connectivity check
python veriflow/cli.py --db ./database run --tile 0001 --only-check

# Solo simulación
python veriflow/cli.py --db ./database run --tile 0001 --only-sim

# Solo síntesis
python veriflow/cli.py --db ./database run --tile 0001 --only-synth

# Saltar síntesis
python veriflow/cli.py --db ./database run --tile 0001 --skip-synth

# Saltar simulación
python veriflow/cli.py --db ./database run --tile 0001 --skip-sim
```

### 6.3 Interpretar el resultado

```
| Stage        | Result        | Details          |
|--------------|---------------|------------------|
| Connectivity | PASS          |                  |
| Simulation   | COMPLETED     | 135 ns           |
| Synthesis    | PASS          | 253 cells        |
```

| Result | Significado |
|---|---|
| `PASS` | Stage exitoso |
| `COMPLETED` | Simulación terminó sin errores |
| `FAIL` | Stage falló |
| `FAILED` | Simulación terminó con errores |
| `SKIPPED` | Stage no fue ejecutado |

**Status global:**
- `PASS` — todo pasó
- `PARTIAL` — algún stage fue skipped
- `FAIL` — connectivity o synthesis fallaron

---

## 7. Waveforms

### Ver waveforms del último run

```bash
python veriflow/cli.py --db ./database waves --tile 0001
```

### Ver waveforms de un run específico

```bash
python veriflow/cli.py --db ./database waves --tile 0001 --run run-003
```

### En GTKWave

1. En el panel SST izquierdo expande `tb` → `DUT`
2. Selecciona las señales que quieres ver (`clk`, `arst_n`, `data_reg_a`, etc.)
3. Haz click en **Append** o **Insert** para agregarlas al visor
4. Presiona **Ctrl+Shift+F** para hacer zoom al rango completo

---

## 8. Gestión de Versiones

### Bump de versión (cambio interno)

Cuando haces un cambio significativo al RTL y quieres marcar una nueva iteración de desarrollo:

```bash
python veriflow/cli.py --db ./database bump-version --tile 0001
```

- Version: `01` → `02`
- Revision: sin cambio
- Dir anterior: preservado como historial
- Dir nuevo: `works/` copiado, `runs/` limpio

### Bump de revisión (autorización del asesor)

Cuando el asesor aprueba el diseño:

```bash
python veriflow/cli.py --db ./database bump-revision --tile 0001
```

- Revision: `01` → `02`
- Version: **reset a `01`**
- Dir anterior: preservado como historial
- Dir nuevo: `works/` copiado, `runs/` limpio

### Trazabilidad

Cada tile ID en `tiles/` representa una instancia independiente con su propio historial de runs:

```
tiles/
├── MST130-01-26032500010101/   ← versión inicial
│   └── runs/run-001/ ... run-005/
├── MST130-01-26032500010201/   ← bump-version
│   └── runs/run-001/ ... run-003/
└── MST130-01-26032500010102/   ← bump-revision (version reset)
    └── runs/run-001/
```

---

## 9. Archivos Generados

Cada run genera en `tiles/<tile_id>/runs/run-NNN/`:

### `manifest.yaml`
Metadata completa del run: tile ID, run ID, fecha, autor, objetivo, status, herramientas, fuentes, artefactos y resultados de cada stage.

### `notes.md`
Notas del diseñador para ese run, tomadas de `run_config.yaml`.

### `summary.md`
Tabla de resultados del run. También se imprime en consola al terminar.

### `README.md`
Documentación del tile actualizada con los datos de `tile_config.yaml`. Se regenera en cada run.

---

## 10. Registros CSV

### `tile_index.csv`
Índice de todos los tiles. Siempre refleja el tile ID más reciente de cada tile number.

### `records.csv`
Historial completo de todos los runs de todos los tiles. Cada run agrega una fila con: Tile_ID, Run_ID, fecha, autor, objetivo, status, resultados de stages, versión de herramienta, path del run y tags.

---

## 11. Tests

```bash
python -m veriflow.tests.runner
```

Los tests usan `tempfile.mkdtemp()` para entornos aislados y se limpian solos. No requieren pytest ni herramientas externas (los tests de run se ejecutan sin iverilog/yosys).

---

## 12. Solución de Problemas Comunes

### `ModuleNotFoundError: No module named 'veriflow'`
El `cli.py` incluye un path fix automático. Si persiste, usa:
```bash
python -m veriflow.cli --db ./database <comando>
```

### `Tool not found in PATH: iverilog`
Activa OSS CAD Suite:
```bat
C:\Users\<usuario>\oss-cad-suite\environment.bat
```

### Connectivity FAIL
Revisa el log:
```bash
type database\tiles\<tile_id>\runs\<run-NNN>\out\connectivity\logs\connectivity.log
```

### Simulation FAILED
Revisa el log:
```bash
type database\tiles\<tile_id>\runs\<run-NNN>\out\sim\logs\sim.log
```

### GTKWave muestra `xxxxxxxx`
Las señales sin inicializar se muestran como `x`. Asegúrate de que el reset `arst_n` esté activo al inicio y que el DUT inicialice sus outputs en el bloque de reset.

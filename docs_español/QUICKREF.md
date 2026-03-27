# VeriFlow V1 — Referencia Rápida

## Activar entorno (Windows)
```bat
C:\Users\<usuario>\oss-cad-suite\environment.bat
cd C:\ruta\a\tu\proyecto
```

---

## Comandos

```bash
# Inicializar base de datos
python veriflow/cli.py --db ./database init
python veriflow/cli.py --db ./database init --force

# Crear tile
python veriflow/cli.py --db ./database create-tile

# Run completo
python veriflow/cli.py --db ./database run --tile 0001

# Run con opciones
python veriflow/cli.py --db ./database run --tile 0001 --waves
python veriflow/cli.py --db ./database run --tile 0001 --skip-synth
python veriflow/cli.py --db ./database run --tile 0001 --only-check

# Abrir waveforms
python veriflow/cli.py --db ./database waves --tile 0001
python veriflow/cli.py --db ./database waves --tile 0001 --run run-003

# Bump de versión / revisión
python veriflow/cli.py --db ./database bump-version --tile 0001
python veriflow/cli.py --db ./database bump-revision --tile 0001

# Tests
python -m veriflow.tests.runner
```

---

## Flujo de trabajo

```
init → llenar project_config.yaml
     → create-tile
     → llenar tile_config.yaml
     → agregar RTL en src/rtl/<top_module>.v
     → editar test en src/tb/tb_tile.v
     → llenar run_config.yaml
     → run --tile XXXX --waves
```

---

## Archivos a editar por tile

```
database/config/tile_0001/
├── tile_config.yaml     ← nombre, autor, top_module, descripción
├── run_config.yaml      ← autor, objetivo, notas del run
└── src/
    ├── rtl/<top_module>.v   ← RTL del usuario
    └── tb/tb_tile.v         ← test entre los marcadores
```

---

## Estructura del test (tb_tile.v)

```verilog
// USER TEST STARTS HERE //
write_data_reg_a(32'd1);
write_data_reg_b(32'd1);
@(posedge clk);
$display("resultado = %0d", data_reg_c);
// USER TEST ENDS HERE //
```

---

## Tasks disponibles en el testbench

| Task | Descripción |
|---|---|
| `write_data_reg_a(data)` | Escribe en data_reg_a |
| `write_data_reg_b(data)` | Escribe en data_reg_b |
| `write_csr_in(data)` | Escribe en csr_in |
| `reset_csr_in` | Limpia bits [15:12] de csr_in |
| `read_csr_out(data)` | Lee csr_out |

**Señales accesibles directamente:** `clk`, `arst_n`, `csr_in`, `data_reg_a`, `data_reg_b`, `data_reg_c`, `csr_out`, `csr_in_re`, `csr_out_we`

---

## Status de un run

| Status | Condición |
|---|---|
| `PASS` | Connectivity PASS + Simulation COMPLETED + Synthesis PASS |
| `PARTIAL` | Algún stage fue SKIPPED |
| `FAIL` | Connectivity FAIL o Synthesis FAIL |

---

## Formato Tile ID

```
MST130-01-26032500010102
│         │      │  │  └─ revision (02)
│         │      │  └──── version (01)
│         │      └─────── tile number (0001)
│         └────────────── fecha YYMMDD (260325)
└──────────────────────── id_prefix
```

---

## Jerarquía de versiones

- `bump-version` → version +1, revisión sin cambio *(cambio del diseñador)*
- `bump-revision` → revisión +1, version reset a 01 *(autorización del asesor)*
- Ambos preservan el dir anterior y crean uno nuevo limpio

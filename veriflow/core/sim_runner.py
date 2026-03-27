import subprocess
import tempfile
from pathlib import Path

from veriflow.core.log_parser import parse_sim_log

USER_TEST_PLACEHOLDER = "/* USER_TEST */"
MODULE_INST_PLACEHOLDER = "/* MODULE_INSTANTIATION */"


def _build_dut_inst(top_module: str) -> str:
    return f"""{top_module} DUT (
    .clk       (clk),
    .arst_n    (arst_n),
    .csr_in    (csr_in),
    .data_reg_a(data_reg_a),
    .data_reg_b(data_reg_b),
    .data_reg_c(data_reg_c),
    .csr_out   (csr_out),
    .csr_in_re (csr_in_re),
    .csr_out_we(csr_out_we)
);"""


def _read_user_test(tb_files: list[Path]) -> str:
    """
    Collect user test code from all files in src/tb/.
    Strips timescale, module declarations, and endmodule — only keeps
    the raw statements inside // USER TEST STARTS HERE // markers if present,
    otherwise includes the full file content.
    """
    import re
    parts = []
    for f in tb_files:
        content = f.read_text(encoding="utf-8")

        # If file has USER TEST markers, extract only what's between them
        m = re.search(
            r"//\s*USER TEST STARTS HERE\s*//(.*)//\s*USER TEST ENDS HERE\s*//",
            content,
            re.DOTALL,
        )
        if m:
            parts.append(m.group(1))
        else:
            # Strip timescale, module/endmodule wrappers if present
            content = re.sub(r"`timescale[^\n]*\n", "", content)
            content = re.sub(r"\bmodule\s+\w+\s*;", "", content)
            content = re.sub(r"\bendmodule\b", "", content)
            parts.append(content)

    return "\n".join(parts).strip()


def _inject_tb(
    tb_base_path: Path,
    top_module: str,
    tb_files: list[Path],
) -> Path:
    """
    Read tb_base.v and inject:
      1. DUT instantiation at /* MODULE_INSTANTIATION */
      2. User test code at /* USER_TEST */
    Write result to a temporary file and return its path.
    """
    content = tb_base_path.read_text(encoding="utf-8")

    # Inject DUT
    content = content.replace(MODULE_INST_PLACEHOLDER, _build_dut_inst(top_module))

    # Inject user test
    user_test = _read_user_test(tb_files) if tb_files else ""
    content = content.replace(USER_TEST_PLACEHOLDER, user_test)

    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".v",
        delete=False,
        encoding="utf-8",
    )
    tmp.write(content)
    tmp.close()
    return Path(tmp.name)


def run_connectivity_check(
    rtl_files: list[Path],
    tb_base_path: Path,
    tb_tasks_path: Path,
    top_module: str,
    log_path: Path,
) -> str:
    """
    Run iverilog connectivity check.
    Returns 'PASS' or 'FAIL'.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Connectivity check uses no user TB files — just DUT injection
    tmp_tb = _inject_tb(tb_base_path, top_module, tb_files=[])

    try:
        include_dir = tb_tasks_path.parent
        cmd = (
            ["iverilog", "-o", "/dev/null" if _is_unix() else "NUL"]
            + ["-I", include_dir.as_posix()]
            + [f.as_posix() for f in rtl_files]
            + [Path(tmp_tb).as_posix()]
        )
        result = subprocess.run(cmd, capture_output=True, text=True)
        log_content = result.stdout + result.stderr
        log_path.write_text(log_content, encoding="utf-8")
        return "PASS" if result.returncode == 0 else "FAIL"
    finally:
        Path(tmp_tb).unlink(missing_ok=True)


def run_simulation(
    rtl_files: list[Path],
    tb_files: list[Path],
    tb_base_path: Path,
    tb_tasks_path: Path,
    top_module: str,
    sim_log_path: Path,
    wave_path: Path,
) -> tuple[str, dict]:
    """
    Compile and run simulation using iverilog/vvp.
    Returns (result, parsed_log_dict).
    result is 'COMPLETED' or 'FAILED'.
    """
    sim_log_path.parent.mkdir(parents=True, exist_ok=True)
    wave_path.parent.mkdir(parents=True, exist_ok=True)

    # Inject DUT + user test into a single tb file
    tmp_tb = _inject_tb(tb_base_path, top_module, tb_files=tb_files)
    include_dir = tb_tasks_path.parent

    import tempfile, os
    tmp_dir = Path(tempfile.mkdtemp())
    compiled = tmp_dir / "sim.out"

    try:
        # Compile — only RTL files + the injected TB
        compile_cmd = (
            ["iverilog", "-o", compiled.as_posix()]
            + ["-I", include_dir.as_posix()]
            + [f.as_posix() for f in rtl_files]
            + [Path(tmp_tb).as_posix()]
        )
        compile_result = subprocess.run(compile_cmd, capture_output=True, text=True)
        compile_log = compile_result.stdout + compile_result.stderr

        if compile_result.returncode != 0:
            sim_log_path.write_text(compile_log, encoding="utf-8")
            return "FAILED", {"sim_time": "", "seed": ""}

        # Run vvp from wave dir so $dumpfile("waves.vcd") lands there
        run_result = subprocess.run(
            ["vvp", compiled.as_posix()],
            capture_output=True,
            text=True,
            cwd=str(wave_path.parent),
        )
        run_log = compile_log + run_result.stdout + run_result.stderr
        sim_log_path.write_text(run_log, encoding="utf-8")

        parsed = parse_sim_log(run_log)
        status = "COMPLETED" if run_result.returncode == 0 else "FAILED"
        return status, parsed
    finally:
        Path(tmp_tb).unlink(missing_ok=True)
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


def launch_gtkwave(wave_path: Path) -> None:
    """Launch GTKWave with the given VCD file (non-blocking)."""
    subprocess.Popen(["gtkwave", str(wave_path)])


def _is_unix() -> bool:
    import platform
    return platform.system() != "Windows"

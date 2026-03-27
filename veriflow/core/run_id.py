import re
from pathlib import Path


def get_next_run_id(runs_dir: Path) -> str:
    """
    Scan the runs directory for existing run-NNN folders and return the next run ID.
    Format: run-NNN (3 digits, zero-padded)
    """
    if not runs_dir.exists():
        return "run-001"

    pattern = re.compile(r"^run-(\d{3})$")
    max_num = 0
    for entry in runs_dir.iterdir():
        if entry.is_dir():
            m = pattern.match(entry.name)
            if m:
                num = int(m.group(1))
                if num > max_num:
                    max_num = num
    return f"run-{max_num + 1:03d}"

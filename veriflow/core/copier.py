import shutil
from pathlib import Path


def copy_flat(src_dir: Path, dst_dir: Path, extension: str = ".v") -> list[Path]:
    """
    Copy all files matching `extension` from src_dir (flat, no subdir preservation)
    to dst_dir. Resolve name collisions with _1, _2 suffixes.
    Returns list of destination paths.
    """
    dst_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for src_file in sorted(src_dir.rglob(f"*{extension}")):
        dst_name = src_file.name
        dst_path = dst_dir / dst_name
        # Resolve collision
        counter = 1
        while dst_path.exists():
            stem = src_file.stem
            dst_path = dst_dir / f"{stem}_{counter}{extension}"
            counter += 1
        shutil.copy2(src_file, dst_path)
        copied.append(dst_path)
    return copied

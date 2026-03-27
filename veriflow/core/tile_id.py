from datetime import date


def generate_tile_id(
    id_prefix: str,
    tile_number: int,
    id_version: int = 1,
    id_revision: int = 1,
    today: date | None = None,
) -> str:
    """
    Format: <id_prefix>-<YYMMDD><tile_number:04d><id_version:02d><id_revision:02d>
    Example: MST130-01-26031500010101
    """
    if today is None:
        today = date.today()
    yymmdd = today.strftime("%y%m%d")
    tile_num_str = f"{tile_number:04d}"
    version_str = f"{id_version:02d}"
    revision_str = f"{id_revision:02d}"
    return f"{id_prefix}-{yymmdd}{tile_num_str}{version_str}{revision_str}"


def parse_tile_id(tile_id: str) -> dict:
    """
    Parse a tile_id into its components.
    Returns dict with keys: id_prefix, yymmdd, tile_number, id_version, id_revision
    The suffix after the last '-' is: YYMMDD(6) + tile_number(4) + version(2) + revision(2) = 14 chars
    """
    # Split on '-' but id_prefix may itself contain '-'
    # The numeric suffix is always the last 14 chars of the last segment
    # We find the last '-' that separates the numeric block
    parts = tile_id.rsplit("-", 1)
    if len(parts) != 2 or len(parts[1]) != 14:
        raise ValueError(f"Cannot parse tile_id: {tile_id!r}")
    id_prefix = parts[0]
    numeric = parts[1]
    yymmdd = numeric[0:6]
    tile_number = int(numeric[6:10])
    id_version = int(numeric[10:12])
    id_revision = int(numeric[12:14])
    return {
        "id_prefix": id_prefix,
        "yymmdd": yymmdd,
        "tile_number": tile_number,
        "id_version": id_version,
        "id_revision": id_revision,
    }

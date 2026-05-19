"""Sync dark_icon PNGs from light icon assets (dev-only)."""

from __future__ import annotations

import shutil
from pathlib import Path

BRAND_DIR = (
    Path(__file__).resolve().parents[1] / "custom_components" / "ogero" / "brand"
)


def main() -> None:
    """Copy icon.png assets to dark_icon.png (same artwork for both themes)."""
    pairs = [
        ("icon.png", "dark_icon.png"),
        ("icon@2x.png", "dark_icon@2x.png"),
    ]
    for src_name, dest_name in pairs:
        src = BRAND_DIR / src_name
        dest = BRAND_DIR / dest_name
        if not src.is_file():
            message = f"Missing source asset: {src}"
            raise SystemExit(message)
        shutil.copy2(src, dest)


if __name__ == "__main__":
    main()

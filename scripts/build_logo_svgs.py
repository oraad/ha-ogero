"""Build logo SVG sources from original artwork."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "assets" / "Ogero"
ORIGINAL = (ROOT / "original" / "logo.svg").read_text(encoding="utf-8")

(ROOT / "logo_en_dark.svg").write_text(ORIGINAL, encoding="utf-8")

light = ORIGINAL.replace("fill:#FFFFFF", "fill:#413A8E")
accent = '<path class="st0" d="M100.3,61.4'
accent_replacement = '<path class="st0" style="fill:#C21F60" d="M100.3,61.4'
if accent not in light:
    message = "Expected accent path not found in logo SVG"
    raise SystemExit(message)
light = light.replace(accent, accent_replacement, 1)
(ROOT / "logo_en.svg").write_text(light, encoding="utf-8")

icon = (ROOT / "icon_mark.svg").read_text(encoding="utf-8")
(ROOT / "icon_mark_dark.svg").write_text(
    icon.replace("#413A8E", "#FFFFFF"),
    encoding="utf-8",
)

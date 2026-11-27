"""Sample the material-specific annual foliage tints used by Birch Glade."""
import json
from math import isfinite
from pathlib import Path

PALETTE = Path(__file__).resolve().parents[1] / "seasonal-foliage.json"
NEUTRAL = (1.0, 1.0, 1.0)


def load_palette():
    return json.loads(PALETTE.read_text(encoding="utf-8"))


def foliage_tint(palette, material_name, day_of_year):
    """Return a linear RGB multiplier. Day 1 is January 1; fractions are valid."""
    if not isfinite(day_of_year):
        raise ValueError("The day of year must be finite")
    keys = palette["profiles"].get(material_name)
    if keys is None:
        return NEUTRAL
    year = palette["days_per_year"]
    day = (day_of_year - 1) % year + 1
    for (start, color), (end, following) in zip(keys, keys[1:] + [[keys[0][0] + year, keys[0][1]]]):
        if day <= end:
            t = (day - start) / (end - start)
            t = t*t*(3 - 2*t)
            return tuple(a + (b-a)*t for a, b in zip(color, following))
    raise ValueError(f"Invalid seasonal profile for {material_name}")

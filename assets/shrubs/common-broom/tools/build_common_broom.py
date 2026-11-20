"""Build a flowering common broom shrub or seeded variant in Blender."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[3]/"tools"))
from build_birch_heather import build_broom

if __name__ == "__main__":
    build_broom()

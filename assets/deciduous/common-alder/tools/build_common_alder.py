"""Build the reference tree or a seeded variant in Blender."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
from build_riparian_trees import build

if __name__ == "__main__":
    build(willow=False)

"""Build the reference ground asset with Blender."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[3]/"tools"))
from build_ground_assets import main

if __name__ == "__main__":
    main("soil")

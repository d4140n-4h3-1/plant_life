"""Build the reference plant or a seeded variant in Blender."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[3]/"tools"))
from build_rowan_foxtail_daisy import build

if __name__ == "__main__":
    build("oxeye-daisy")

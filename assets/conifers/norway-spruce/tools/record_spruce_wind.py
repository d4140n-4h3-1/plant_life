"""Record a Norway spruce wind GIF from the open Blender model."""
from pathlib import Path
import sys

ASSET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ASSET.parent/"pine"/"tools"))
from record_wind import main


if __name__ == "__main__":
    main("Norway Spruce", ASSET/"renders"/"spruce-wind.gif")

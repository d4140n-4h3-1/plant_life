"""Build a tall tufted hairgrass clump or a seeded variant in Blender."""
from functools import partial
from pathlib import Path
import sys

ASSET = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ASSET.parent/"sheep-fescue"/"tools"))
from build_fescue import fescue_mesh
from build_pine import main

SHOTS = [
    ("hairgrass-full",(12,-18,9),(0,0,3.32),8.9,(790,850)),
    ("hairgrass-detail",(8,-13,8),(0,0,5.2),5.3,(820,690)),
]

if __name__ == "__main__":
    main(ASSET,partial(fescue_mesh,tall=True),"Tufted hairgrass",SHOTS,
         reference_size=(.70,.70,.95),studio_scale=.95/7.2,samples=22)

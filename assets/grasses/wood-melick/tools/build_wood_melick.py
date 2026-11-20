"""Build wood melick grass and seeded variants in Blender."""
from functools import partial
from pathlib import Path
import sys

ASSET = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ASSET.parent/"sheep-fescue"/"tools"))
from build_fescue import fescue_mesh
from build_pine import main

SHOTS = [
    ("melick-full",(12,-18,9),(0,0,3.04),10.8,(840,770)),
    ("melick-detail",(8,-13,8),(0,0,4.7),5.7,(850,710)),
]

if __name__ == "__main__":
    main(ASSET,partial(fescue_mesh,melick=True),"Wood melick",SHOTS,
         reference_size=(.68,.68,.62),studio_scale=.62/7.2,samples=22)

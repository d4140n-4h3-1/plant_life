"""Render the reference spruce between two seeded variants."""
import argparse
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import bpy

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from build_spruce import ASSET, spruce_mesh
from build_pine import point_at, studio_camera


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs=2, type=int, default=(2, 11))
    parser.add_argument("--output", type=Path,
                        default=ASSET/"renders"/"spruce-variants.png")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])

    bpy.ops.wm.read_factory_settings(use_empty=True)
    with TemporaryDirectory(prefix="spruce-examples-") as temp:
        maps = Path(temp)
        trees = [spruce_mesh(maps, seed)
                 for seed in (args.seeds[0], None, args.seeds[1])]
        bpy.context.view_layer.update()
        spacing = max(tree.dimensions.x for tree in trees) + 1.7
        height = max(tree.dimensions.z for tree in trees)
        for tree, column in zip(trees, (-1,0,1)):
            tree.location.x = column*spacing

        framing = height/7.2
        scene, camera = studio_camera(framing, ground_size=2000)
        camera.location = (0, -38*framing, height*.79)
        point_at(camera, (0,0,height*.48))
        camera.data.ortho_scale = max(3.25*spacing, 1.83*height)
        scene.cycles.samples = 16
        scene.render.resolution_x, scene.render.resolution_y = 1180, 720
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()

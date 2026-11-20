"""Render a scatter example made from shared seeded tuft meshes."""
import argparse
from math import tau
from pathlib import Path
from random import Random
import sys
from tempfile import TemporaryDirectory

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fescue import ASSET, fescue_mesh
from build_pine import point_at, studio_camera


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed",type=int,default=27)
    parser.add_argument("--output",type=Path,default=ASSET/"renders"/"fescue-patch.png")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    rng = Random(args.seed)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with TemporaryDirectory(prefix="fescue-patch-") as temp:
        maps = Path(temp)
        source = fescue_mesh(maps,rng.randrange(100000))
        material = source.data.materials[0]
        templates = [source]+[fescue_mesh(maps,rng.randrange(100000),material) for _ in range(4)]
        locations = [(x*.259+rng.uniform(-.08,.08),y*.237+rng.uniform(-.08,.08),0)
                     for x in range(-3,4) for y in range(-2,3)
                     if (x/3.5)**2+(y/2.5)**2 <= 1]
        for i, location in enumerate(locations):
            template = templates[i%len(templates)]
            obj = template if i < len(templates) else bpy.data.objects.new("Fescue tuft",template.data)
            if i >= len(templates):
                bpy.context.collection.objects.link(obj)
            obj.location = location
            obj.rotation_euler.z = rng.uniform(0,tau)
            obj.scale = (1,1,rng.uniform(.79,1.19))

        scene,camera = studio_camera(.235)
        bpy.context.object.data.materials[0].diffuse_color = (.16,.119,.075,1)
        camera.location = (1.46,-2.48,1.33)
        point_at(camera,(0,0,.106))
        camera.data.ortho_scale = 2.25
        scene.cycles.samples = 20
        scene.render.resolution_x,scene.render.resolution_y = 1050,720
        output = args.output.resolve()
        output.parent.mkdir(parents=True,exist_ok=True)
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)


if __name__=="__main__":
    main()

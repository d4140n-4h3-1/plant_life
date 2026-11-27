"""Build four ground-level fallen stick props with Blender."""
import argparse
from math import cos, pi, sin
from pathlib import Path
from random import Random, SystemRandom
import sys

import bpy
import numpy as np
from mathutils import Vector

ASSET = Path(__file__).resolve().parents[1]
ASSETS = ASSET.parents[1]
sys.path.insert(0, str(ASSETS / "tools"))
from build_birch_heather import BranchMesh, SIZE, finish
from build_pine import bark_swatch_maps

VARIANTS = (
    ("bare-twig", .52, .010, 3, 0, 173),
    ("bare-fork", .91, .023, 5, 0, 307),
    ("leafy-twig", .63, .012, 4, 7, 544),
    ("leafy-fork", 1.08, .024, 6, 12, 889),
)


def dry_leaf_maps():
    y, x = np.mgrid[:SIZE, :SIZE] / SIZE
    grain = np.random.default_rng(409).random(x.shape)
    midrib = np.exp(-220 * abs(x-.5))
    veins = np.exp(-14 * abs(np.sin(2*pi*(7.2*y-5.4*abs(x-.5)))))
    mottling = np.sin(26*x + np.sin(18*y)) * np.cos(22*y - 6*x)
    relief = .42 + .21*midrib + .084*veins + .045*grain
    tone = .43 + .15*mottling + .17*grain + .10*veins + .20*midrib
    dark, light = np.array((.19,.085,.034)), np.array((.61,.35,.145))
    return dark + (light-dark)*tone[...,None], relief, .82+.1*grain, .89+.05*grain, .9


def leaf(mesh, root, heading, length, width, curl, lobed):
    """A curved leaf with a raised midrib, rough edges, and a folded tip."""
    side = Vector((-heading.y, heading.x, 0))
    rings = []
    fractions = (0,.13,.26,.38,.51,.63,.75,.87,1)
    for index, t in enumerate(fractions):
        center = root + heading * (length*(t-.16*t**3))
        center.z += length*(.12*sin(pi*t)+curl*t**3)
        if index in (0,len(fractions)-1):
            rings.append((mesh.vertex(center),))
            continue
        shape = sin(pi*t)**.72 * (1.05-.29*t)
        margin = width*.5*shape*(.69 if lobed and index%2==0 else 1)
        edge_left, edge_right = center-side*margin, center+side*margin*.92
        edge_left.z += length*(.030+.03*sin(9*t))
        edge_right.z -= length*(.027+.018*sin(8*t))
        rings.append(tuple(mesh.vertex(point) for point in (edge_left,center,edge_right)))

    for i,(a,b) in enumerate(zip(rings,rings[1:])):
        t0,t1=fractions[i:i+2]
        if len(a)==1:
            for j in range(2):
                mesh.face((a[0],b[j+1],b[j]), ((.5,t0),((j+1)*.5,t1),(j*.5,t1)), 1)
        elif len(b)==1:
            for j in range(2):
                mesh.face((a[j],a[j+1],b[0]), ((j*.5,t0),((j+1)*.5,t0),(.5,t1)), 1)
        else:
            for j in range(2):
                mesh.face((a[j],a[j+1],b[j+1]), ((j*.5,t0),((j+1)*.5,t0),((j+1)*.5,t1)), 1)
                mesh.face((a[j],b[j+1],b[j]), ((j*.5,t0),((j+1)*.5,t1),(j*.5,t1)), 1)


def stick_mesh(length, radius, forks, leaves, seed, *, vary_curve=False):
    rng = Random(seed)
    mesh = BranchMesh()
    bend, frequency, drift, lift = .044, 8, .036, .62
    if vary_curve:
        bend = rng.uniform(-.089, .089)
        frequency = rng.uniform(5, 12)
        drift = rng.uniform(-.105, .105)
        lift = rng.uniform(.28, 1.14)
    backbone = [
        Vector(((t-.5)*length, length*(bend*sin(frequency*t)+drift*t),
                radius*(1.1+lift*sin(5*t)**2)))
        for t in (0,.15,.32,.49,.66,.84,1.0)
    ]
    sides = 8
    mesh.shoot(backbone, tuple(radius*(1-.88*i/6) for i in range(6)), sides, .18)
    mesh.cap(list(range(sides)), backbone[0]+Vector((-.12*radius,0,0)), .18,.12, reverse=True)
    tips = []
    for i in range(forks):
        sign = -1 if i%2 else 1
        segment = min(i+1, len(backbone)-2)
        root = backbone[segment].lerp(backbone[segment+1],rng.uniform(.08,.43))
        reach = length*rng.uniform(.12,.27)
        heading = Vector((rng.uniform(.34,.76),sign*rng.uniform(.57,1),0)).normalized()
        elbow = root+heading*reach*.51+Vector((0,0,radius*rng.uniform(.18,1.0)))
        tip = elbow+heading*reach*.49+Vector((0,0,radius*rng.uniform(-.66,1.2)))
        thickness = radius*rng.uniform(.21,.51)
        mesh.shoot((root,elbow,tip),(thickness,thickness*.41),5,.4)
        tips.append((elbow,tip))
        twig = elbow.lerp(tip,.47)
        twig_end = twig+Vector((reach*.38,sign*reach*.25,radius*.48))
        mesh.shoot((twig,twig_end),(thickness*.33,),4,.56)
        tips.append((twig,twig_end))
    for i in range(leaves):
        a,b=tips[i%len(tips)]
        joint=a.lerp(b,rng.uniform(.28,.82))
        angle=rng.uniform(-pi,pi)
        heading=Vector((cos(angle),sin(angle),0))
        stem=joint+heading*rng.uniform(.008,.020)
        stem.z+=radius*.45
        mesh.shoot((joint,stem),(.00085,),3,.71)
        leaf(mesh,stem,heading,rng.uniform(.039,.093),rng.uniform(.021,.046),
             rng.uniform(-.20,.20), leaves>8)
    minimum = min(vertex.z for vertex in mesh.positions)
    for vertex in mesh.positions:
        vertex.z -= minimum
    return mesh


def random_variants(seed, count, kind):
    rng = Random(seed)
    # Alternate in mixed mode so both types appear in every batch of two or more.
    starts_bare = rng.choice((False, True))
    for index in range(count):
        leafy = kind == "leafy" or (kind == "mixed" and (bool(index % 2) == starts_bare))
        label = "leafy" if leafy else "bare"
        length = rng.uniform(.38, 1.14)
        radius = length * rng.uniform(.011, .025)
        forks = rng.randint(2, 7)
        leaves = rng.randint(4, min(14, 2*forks + 3)) if leafy else 0
        yield (f"{label}-{index+1:02d}", length, radius, forks, leaves, rng.getrandbits(64))


def build(variants, output, *, seed=None):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    maps = output / "textures"
    maps.mkdir(parents=True, exist_ok=True)
    bark = bark_swatch_maps(ASSETS/"deciduous/english-oak/source/bark_swatch.png")
    objects = []
    for slug,length,radius,forks,leaves,mesh_seed in variants:
        bpy.ops.object.select_all(action="DESELECT")
        sources = [("bark", (*bark,2.4))]
        if leaves:
            sources.append(("dry leaves", dry_leaf_maps()))
        mesh = stick_mesh(length,radius,forks,leaves,mesh_seed,vary_curve=seed is not None)
        obj = finish(mesh,maps,slug,sources,None,(),smooth_kinds=(0,1))
        if leaves:
            obj.data.materials[1].use_backface_culling = False
        bpy.ops.export_scene.gltf(filepath=str(output/f"{slug}.glb"),use_selection=True,
                                  export_format="GLB",export_tangents=True)
        objects.append(obj)
    for i,obj in enumerate(objects):
        obj.location.y=(i-1.5)*.42
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output/"fallen-sticks.blend"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    variation = parser.add_mutually_exclusive_group()
    variation.add_argument("--seed", type=int, help="Reproduce a randomized batch.")
    variation.add_argument("--random", action="store_true", help="Generate and print a fresh seed.")
    parser.add_argument("--count", type=int, help="Number of sticks in a batch (default: 8).")
    parser.add_argument("--kind", choices=("mixed", "bare", "leafy"),
                        help="Leaf coverage in a randomized batch (default: mixed).")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    if args.count is not None and args.count < 1:
        parser.error("--count must be positive")
    seed = SystemRandom().getrandbits(64) if args.random else args.seed
    if seed is None:
        if args.count is not None or args.kind is not None:
            parser.error("--count and --kind require --seed or --random")
        variants, output = VARIANTS, args.output_dir or ASSET
    else:
        kind = args.kind or "mixed"
        count = args.count or 8
        output = args.output_dir or ASSET / "variants" / f"{kind}-{seed}-{count}"
        print(f"Fallen sticks seed: {seed}", flush=True)
        variants = random_variants(seed, count, kind)
    build(variants, output.resolve(), seed=seed)


if __name__ == "__main__":
    main()

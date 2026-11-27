"""Build floating sweet-grass and creeping bent with individual blade ribbons."""
from math import cos, sin, tau
from random import Random
import sys

from mathutils import Vector

from build_birch_heather import ASSETS, BranchMesh, UP, finish, main

sys.path.insert(0, str(ASSETS / "grasses/sheep-fescue/tools"))
from build_fescue import grass_maps


def ribbon(mesh, path, widths, band):
    """Loft a blade with its UV root at zero and a tapered final vertex."""
    rings = []
    for index, width in enumerate(widths):
        tangent = path[index + 1] - path[max(index - 1, 0)]
        edge = UP.cross(tangent).normalized() * (width * .5)
        rings.append((mesh.vertex(path[index] - edge), mesh.vertex(path[index] + edge)))
    low, high = (band + .018) / 3, (band + .982) / 3
    for i, ((a, b), (d, c)) in enumerate(zip(rings, rings[1:])):
        v, next_v = i / len(rings), (i + 1) / len(rings)
        mesh.face((a, b, c), ((low, v), (high, v), (high, next_v)))
        mesh.face((a, c, d), ((low, v), (high, next_v), (low, next_v)))
    a, b = rings[-1]
    v = (len(rings) - 1) / len(rings)
    mesh.face((a, b, mesh.vertex(path[-1])), ((low, v), (high, v), ((low + high) * .5, 1)))


def bank_grass(maps, seed, floating):
    rng = Random((2281 if floating else 521) if seed is None else seed)
    mesh = BranchMesh()
    for i in range(47 if floating else 69):
        angle = i * 2.39996 + rng.uniform(-.36, .36)
        outward = Vector((cos(angle), sin(angle), 0))
        cross = UP.cross(outward)
        root = outward * rng.uniform(.015, .095 if floating else .24)
        reach = rng.uniform(.18, .43) if floating else rng.uniform(.065, .18)
        rise = rng.uniform(.10, .25) if floating else rng.uniform(.055, .14)
        width = rng.uniform(.008, .018) if floating else rng.uniform(.0027, .006)
        arch = rng.uniform(2.28, 3.00) if floating else rng.uniform(1.55, 2.45)
        twist = rng.uniform(-.31, .31)
        path = [
            root + reach * t**1.55 * (outward * cos(t*twist) + cross * sin(t*twist))
            + UP * (rise * sin(arch*t))
            for t in (0, .22, .46, .70, .88, 1)
        ]
        ribbon(mesh, path, (width*.54, width, width*.94, width*.69, width*.36), i % 5 == 0)

    for i in range(5 if floating else 9):
        angle = i * tau / (5 if floating else 9) + rng.uniform(-.2,.2)
        outward = Vector((cos(angle), sin(angle), 0))
        across = UP.cross(outward)
        root = outward * rng.uniform(.03, .08 if floating else .20)
        height = rng.uniform(.29, .46) if floating else rng.uniform(.14, .23)
        lean = rng.uniform(.055, .12)
        stalk = lambda t: root + outward * lean * t*t + UP * height * t
        ribbon(mesh, [stalk(t) for t in (0,.48,.75,.91,1)], (.0021,.0017,.0012,.0008), 0)
        for j in range(6):
            joint = stalk(.67 + .054*j)
            fork = across * (-1 if j % 2 else 1) + outward*.32 + UP*.8
            length = rng.uniform(.024,.065) if floating else rng.uniform(.015,.038)
            tip = joint + fork.normalized() * length
            ribbon(mesh, (joint, joint.lerp(tip,.62), tip), (.0012,.0010), 0)
            head = tip + (fork + UP).normalized()*rng.uniform(.007,.019)
            ribbon(mesh, (tip, tip.lerp(head,.45), head),
                   (.0011, .0024 if floating else .0015), 2)

    name = "Floating sweet-grass" if floating else "Creeping bent"
    obj = finish(mesh, maps, name, (("grass", grass_maps(tall=floating)),),
                 seed, ((.85,1.16),(.85,1.16),(.85,1.15)))
    obj.data.materials[0].use_backface_culling = False
    return obj


def build(floating):
    slug = "floating-sweet-grass" if floating else "creeping-bent"
    name = "Floating sweet-grass" if floating else "Creeping bent"
    height = .46 if floating else .23
    shots = [(slug+"-full", (10,-17,9), (0,0,2.35),
              17.0 if floating else 22.0, (750,680))]
    main(ASSETS/"grasses"/slug, lambda maps, seed: bank_grass(maps, seed, floating),
         name, shots, (.95,.95,height), height/7.2, 20)

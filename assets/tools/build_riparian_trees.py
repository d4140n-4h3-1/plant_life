"""Build common alder and white willow for the deciduous tree catalog."""
from math import cos, exp, pi, sin, tau
from random import Random

import bpy
import numpy as np
from mathutils import Vector

from build_birch_heather import ASSETS, BranchMesh, SIZE, UP, atlas, finish, main


def bark_maps(willow):
    """Load the tileable photographic bark maps bundled with each tree."""
    slug = "white-willow" if willow else "common-alder"
    source = ASSETS / "deciduous" / slug / "source"

    def read_map(kind):
        image = bpy.data.images.load(str(source / f"bark-{kind}.jpg"))
        try:
            image.colorspace_settings.name = "Non-Color"
            if tuple(image.size) != (SIZE, SIZE):
                raise ValueError(f"Expected a {SIZE} × {SIZE} bark map: {image.filepath}")
            pixels = np.empty(SIZE * SIZE * 4, dtype=np.float32)
            image.pixels.foreach_get(pixels)
            return pixels.reshape(SIZE, SIZE, 4)[::-1]
        finally:
            bpy.data.images.remove(image)

    def blur(values, radius):
        frequencies = np.fft.fftfreq(SIZE)
        kernel = np.exp(-2*np.pi**2*radius**2
                        * (frequencies[:, None]**2 + frequencies[None, :]**2))
        return np.fft.ifft2(np.fft.fft2(values)*kernel).real

    color = read_map("diff")[..., :3]
    if not willow:
        color = color * np.array((.83, .80, .77))
    # The scanned displacement is mostly broad undulation; keep the fissures and
    # plates that shade the bark at texture scale, as bark_swatch_maps does.
    displacement = read_map("disp")[..., 0]
    height = np.clip(.5 + 2.8*(blur(displacement, .75) - blur(displacement, 21)), 0, 1)
    # Soften the scanned occlusion so the trunk is not darkened twice by the renderer's own.
    occlusion = 1 - .4*(1 - read_map("ao")[..., 0])
    return (color, height, read_map("rough")[..., 0], occlusion,
            5.5 if willow else 5.0)


def tree_mesh(maps, seed, willow):
    rng = Random((247 if willow else 815) if seed is None else seed)
    tree = BranchMesh()
    height = 11.4 if willow else 13.0
    radius = .44 if willow else .29

    def center(fraction):
        return Vector((.48*sin(3.9*fraction) if willow else .17*sin(6.1*fraction),
                       .24*sin(5*fraction)*fraction, height*fraction))

    fractions = (0,.009,.027,.061,.13,.22,.33,.45,.56,.67,.77,.86,.94,.985)
    rings = []
    for f in fractions:
        ring = []
        for side in range(16):
            angle = tau*side/16
            root = radius*.95*exp(-height*f*6)*max(0, cos(5*angle+.3))**4
            r = radius*(1-f)**.84*(1+.08*cos(3*angle + f*8)) + root
            ring.append(tree.vertex(center(f) + Vector((r*cos(angle), r*sin(angle), 0))))
        rings.append(ring)
    tree.cap(rings[0], center(0), 0, -.1, reverse=True)
    for i, (a, b) in enumerate(zip(rings, rings[1:])):
        tree.join(a, b, height*fractions[i]*.53, height*fractions[i+1]*.53)
    tree.cap(rings[-1], center(1), height*fractions[-1]*.53, height*.53)

    for tier in range(12):
        level = tier / 11
        fraction = (.24 if willow else .33) + (.63 if willow else .61)*level
        branch_count = 3 if tier < 8 else 2
        for branch in range(branch_count):
            angle = tier*2.4 + branch*tau/branch_count + rng.uniform(-.28,.28)
            outward = Vector((cos(angle), sin(angle), 0))
            across = UP.cross(outward)
            start = center(fraction + rng.uniform(-.014,.014))
            crown = sin(pi*(.29+.68*level))**.82
            spread = (.4 + (4.05 if willow else 2.45)*crown)*rng.uniform(.79,1.16)
            thickness = (.159 if willow else .106)*(1-.91*level)*rng.uniform(.8,1.21)
            rise = spread*(.51 if willow else .45)
            elbow = start + outward*spread*.36 + UP*rise*.54
            shoulder = start + outward*spread*.72 + UP*rise
            tip = start + outward*spread + UP*rise*(.68 if willow else 1.47)
            tree.shoot((start,elbow,shoulder,tip),
                       (thickness,.62*thickness,.27*thickness), 6, level)

            for a, b in ((elbow, shoulder), (shoulder, tip)):
                for perch in (.22,.57,.85):
                    base = a.lerp(b,perch)
                    for side in (-1,1):
                        direction = outward*rng.uniform(.35,.77) + across*side*rng.uniform(.45,.91)
                        direction += UP*(rng.uniform(-1.1,-.35) if willow else rng.uniform(.25,.79))
                        length = (.51+spread*(.29 if willow else .23))*rng.uniform(.75,1.24)
                        twig = base + direction.normalized()*length*.73
                        tree.shoot((base,twig),(.18*thickness,),3,level)
                        tree.spray(base,direction,length,length*(.61 if willow else .9),1.18)
                        tree.spray(base.lerp(twig,.51),direction + UP*(-.32 if willow else .41),
                                   length*.71,length*.62,.98)
    for i in range(7):
        angle = i*2.4
        tree.spray(center(.89+i*.013),Vector((cos(angle),sin(angle),.44)),.78,.64,1.06)
    name = "White willow" if willow else "Common alder"
    return finish(tree,maps,name,(("bark",bark_maps(willow)),
                                 ("leaves",atlas("willow" if willow else "alder"))),
                  seed,((.78,1.19),(.78,1.19),(.83,1.18)))


def build(willow):
    slug, name, height, width = (("white-willow","White willow",11.4,11.0) if willow else
                                 ("common-alder","Common alder",13.0,7.7))
    shots = [(slug+"-full", (10,-17,9), (0,0,3.65), 10.2, (620,760))]
    main(ASSETS/"deciduous"/slug, lambda maps,seed: tree_mesh(maps,seed,willow),
         name, shots, (width,width,height), height/7.2, 20)

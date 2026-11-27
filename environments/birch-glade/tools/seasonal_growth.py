"""Make seasonal foliage and flower geometry for a Birch Glade snapshot."""
import hashlib
from math import floor

import bmesh

# Material and the start/end of spring growth, then autumn leaf fall.
LEAF_FALL = {
    "Silver Birch Leaves": (99, 134, 263, 315),
    "English Oak Leaves": (114, 153, 288, 334),
    "European Larch Needles": (100, 136, 281, 325),
    "Common alder Leaves": (104, 144, 287, 329),
    "White willow Leaves": (88, 127, 288, 334),
}
FLOWERS = {
    "English Bluebell Bells": (101, 154),
    "Oxeye Daisy Petals": (145, 265),
    "Oxeye Daisy Pollen": (145, 265),
    "Common Heather Blossoms": (194, 285),
}
AUTUMN_COLOR = "seasonal_autumn_color"
AUTUMN_AMOUNT = "seasonal_autumn_amount"
PEAK_COLOR_DAY = {
    "Silver Birch Leaves": 300,
    "English Oak Leaves": 301,
    "European Larch Needles": 296,
    "Common alder Leaves": 299,
    "White willow Leaves": 299,
}


def smooth(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def patch_random(name, position):
    # Neighboring cards share a color phase instead of alternating at random.
    cell = tuple(floor(coordinate / .95) for coordinate in position)
    key = repr((name, cell)).encode()
    return int.from_bytes(hashlib.blake2s(key, digest_size=4).digest(), "little") / 2**32


def crown_timing(first, last, variation, drop_chance, outer):
    """Return when a spray finishes turning and when it falls."""
    turn = first - 5 + (last - first - 9) * (.66 * variation + .34 * (1 - outer))
    candidate = first + (last - first) * (.75 * drop_chance + .25 * (1 - outer))
    return turn, max(turn + 8, candidate)


def apply_growth(meshes, day):
    day = (day - 1) % 365 + 1
    for mesh in meshes:
        materials = {index: material for index, material in enumerate(mesh.materials) if material}
        canopy = {i: material for i, material in materials.items() if material.name in LEAF_FALL}
        hidden = {i for i, material in materials.items()
                  if material.name in FLOWERS and not FLOWERS[material.name][0] <= day <= FLOWERS[material.name][1]}
        if not canopy and not hidden:
            continue
        bm = bmesh.new()
        try:
            bm.from_mesh(mesh)
            foliage = {face for face in bm.faces if face.material_index in canopy}
            removed = [face for face in bm.faces if face.material_index in hidden]
            autumn_slots = {}
            for face in bm.faces:
                if face not in foliage:
                    continue
                foliage.remove(face)
                material = canopy[face.material_index]
                spring_start, spring_end, first, last = LEAF_FALL[material.name]
                group = [face]
                for part in group:
                    for edge in part.edges:
                        for neighbor in edge.link_faces:
                            if neighbor in foliage and neighbor.material_index == face.material_index:
                                foliage.remove(neighbor)
                                group.append(neighbor)

                center = sum((part.calc_center_median() for part in group), face.calc_center_median()*0) / len(group)
                variation = patch_random(material.name, center)
                # Sheltered inner sprays turn later. Every spray turns before it drops.
                outer = smooth((center.xy.length - .45) / 2.1)
                drop_chance = patch_random(material.name + " leaf fall", center)
                turn, fall = crown_timing(first, last, variation, drop_chance, outer)
                if day < spring_end:
                    dormancy = 1.0 - smooth((day - spring_start) / (spring_end - spring_start))
                    if dormancy == 1.0 or drop_chance < dormancy:
                        removed.extend(group)
                elif day >= fall:
                    removed.extend(group)
                elif day >= turn - 12:
                    tint_step = min(3, int(smooth((day - turn + 12) / 12) * 4))
                    if tint_step == 0:
                        continue
                    key = (face.material_index, tint_step)
                    if key not in autumn_slots:
                        tinted = material.copy()
                        tinted.name = f"{material.name} · autumn {tint_step}"
                        tinted[AUTUMN_COLOR] = material.name
                        tinted[AUTUMN_AMOUNT] = tint_step / 3
                        autumn_slots[key] = len(mesh.materials)
                        mesh.materials.append(tinted)
                    for part in group:
                        part.material_index = autumn_slots[key]
            if removed:
                bmesh.ops.delete(bm, geom=removed, context="FACES")
            if removed or autumn_slots:
                bm.to_mesh(mesh)
                mesh.update()
        finally:
            bm.free()


def add_litter(scene, canopy, surface_z, in_water, day, seed):
    """Scatter low, irregular groups of fallen broad leaves on dry ground."""
    from math import cos, sin, tau
    from random import Random

    import bpy
    from mathutils import Vector

    day = (day - 1) % 365 + 1
    rng = Random(seed ^ 0x893FE)
    vertices, faces, colors = [], [], []
    shades = ((.23, .076, .025, 1), (.35, .15, .025, 1), (.45, .235, .05, 1))
    for tree in canopy:
        names = {material.name for material in tree.data.materials if material}
        trees = names.intersection(LEAF_FALL) - {"European Larch Needles"}
        if not trees:
            continue
        _, _, first, last = LEAF_FALL[min(trees)]
        if day < first:
            continue
        amount = smooth((day - first) / (last - first))
        for _ in range(round(28 * amount)):
            angle = rng.uniform(0, tau)
            radius = rng.uniform(.40, 2.9)
            center = tree.location.xy + Vector((cos(angle)*radius, sin(angle)*radius))
            if in_water(*center):
                continue
            heading = rng.uniform(0, tau)
            axis = Vector((cos(heading), sin(heading)))
            across = Vector((-axis.y, axis.x))
            length = rng.uniform(.035, .084)
            width = length * rng.uniform(.40, .64)
            shape = ((-.50, 0),(-.24, -.39),(.10, -.50),(.5, 0),(.16, .43),(-.23,.48))
            start = len(vertices)
            for u, v in shape:
                point = center + axis*(u*length) + across*(v*width)
                vertices.append((*point, surface_z(*point) + .009 + .006*abs(v)))
            faces.append(tuple(range(start, start+len(shape))))
            colors.append(rng.randrange(len(shades)))

    if not faces:
        return
    mesh = bpy.data.meshes.new("Fallen autumn leaves")
    mesh.from_pydata(vertices, [], faces)
    for index, color in enumerate(shades, 1):
        material = bpy.data.materials.new(f"Dead leaf {index}")
        material.diffuse_color = color
        material.use_nodes = True
        shader = material.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Base Color"].default_value = color
        shader.inputs["Roughness"].default_value = .9
        mesh.materials.append(material)
    for face, color in zip(mesh.polygons, colors):
        face.material_index = color
    scene.collection.objects.link(bpy.data.objects.new(mesh.name, mesh))

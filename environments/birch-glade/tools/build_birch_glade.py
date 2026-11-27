"""Build a birch glade using the plant_life asset library."""
import argparse
from collections import Counter
from math import cos, exp, isfinite, sin, tau
from pathlib import Path
from random import Random, SystemRandom
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

OUTPUT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OUTPUT.parent / "granite-woodland" / "tools"))
import build_granite_woodland as woodland

sys.path.insert(0, str(woodland.ROOT / "assets" / "terrain" / "hydroxus-terrain"))
import hydroxus_rivers
from hydroxus_water_join import join_water_channels
sys.path.insert(0, str(Path(__file__).resolve().parent))
from seasonal_materials import apply_blender
from seasonal_growth import add_litter, apply_growth
from weather import (DEFAULT_SNOW_HOURS, FULL_SNOW_HOURS, PRESETS,
                     animate_accumulation, apply_atmosphere, apply_ground)


BANK_GRASSES = {
    "Floating sweet-grass": "grasses/floating-sweet-grass/floating-sweet-grass.glb",
    "Creeping bent": "grasses/creeping-bent/creeping-bent.glb",
    "Tufted hairgrass": "grasses/tufted-hairgrass/tufted-hairgrass.glb",
}


def trail_x(y):
    return -2.7 + 4.5 * exp(-((y - 4) / 8.0) ** 2)


def trail_edge(y):
    return 0.86 + 0.12 * sin(y * 0.43)


def river_x(y):
    return -5.3 + 1.05 * sin(0.22 * y)


def stream_y(x):
    return 5.6 + 0.55 * sin(0.55 * (x + 14))


def elevation(x, y):
    grade = 0.065 * (y + 14)
    distance = x - river_x(y)
    river_bank = 0.10 * distance ** 2 / (1 + abs(distance) * 0.25 + 0.09 * distance ** 2)
    if distance < 0:
        river_bank = 0.10 * distance ** 2 / (1 + abs(distance) * 0.25)
        across = y - stream_y(x)
        stream_grade = 0.065 * (stream_y(x) + 14) - 0.11 * distance
        stream_bank = 0.28 * across ** 2 / (1 + abs(across) * 0.18)
        return min(grade + river_bank, stream_grade + stream_bank)
    ridge = 0.70 * exp(-((x - 6.5) / 3.5) ** 2 - ((y - 5) / 6) ** 2)
    floor = 0.12 * sin(x * 0.7 + y * 0.4) + 0.09 * cos(y * 0.9)
    terrace = min(1, distance / 3)
    undulation = 0.06 * sin(1.1 * x - 0.46 * y) * cos(0.84 * y)
    return grade + river_bank + terrace * (ridge + floor + undulation)


def carve_channel(terrain, group, name, source, width, depth, shore_rng, join=None):
    scene = bpy.context.scene
    scene.cursor.location = (*source, 0)
    scene.hxr_width = width
    scene.hxr_depth = depth
    scene.hxr_steps = 2000
    if join is not None:
        mesh = terrain.data
        points = [vertex.co.copy() for vertex in mesh.vertices]
        adjacency = [set() for _ in points]
        for a, b in (edge.vertices for edge in mesh.edges):
            adjacency[a].add(b)
            adjacency[b].add(a)
        start = min(range(len(points)), key=lambda i:
                    (points[i].x - source[0]) ** 2 + (points[i].y - source[1]) ** 2)
        route = hydroxus_rivers.downhill(points, adjacency, start, scene.hxr_steps)
        steps = next((i for i, index in enumerate(route) if join(points[index])), None)
        if steps is None or steps < 2:
            raise RuntimeError("The tributary route did not reach the river")
        scene.hxr_steps = steps
    existing = set(bpy.data.objects)
    if bpy.ops.hx.river(build_bed=False, smooth_path=join is not None) != {"FINISHED"}:
        raise RuntimeError(f"Hydroxus failed to carve {name}")
    water, = set(bpy.data.objects) - existing
    water.name = name
    water.data.name = name
    water["channel_half_width_m"] = width
    water["channel_depth_m"] = depth
    if join is not None:
        water["flows_into"] = "Birch River"
    for collection in list(water.users_collection):
        collection.objects.unlink(water)
    group.objects.link(water)
    mesh = water.data
    centers = [(mesh.vertices[i].co + mesh.vertices[i + 1].co) / 2
               for i in range(0, len(mesh.vertices), 2)]
    # The stream already uses the same smoothed route for its bed and ribbon.
    if join is None:
        smooth = [centers[0]]
        for i in range(1, len(centers) - 1):
            neighbors = centers[max(0, i - 3):i + 4]
            smooth.append(sum(neighbors, Vector()) / len(neighbors))
        smooth.append(centers[-1])
        centers = smooth
    # Each bank gets independent, spatially coherent variations at three scales.
    phases = [[shore_rng.uniform(0, tau) for _ in range(3)] for _ in range(2)]
    sections = []
    distance = 0.0
    for i, center in enumerate(centers):
        tangent = centers[min(i + 1, len(centers) - 1)] - centers[max(i - 1, 0)]
        lateral = Vector((-tangent.y, tangent.x, 0)).normalized()
        if i:
            distance += (center.xy - centers[i - 1].xy).length
        bank_widths = tuple(
            width * (0.49 + 0.075 * sin(0.86 * distance + broad)
                     + 0.038 * sin(1.74 * distance + middle)
                     + 0.017 * sin(3.4 * distance + fine))
            for broad, middle, fine in phases
        )
        # Extend the render surface under the banks so the terrain defines the edge.
        margin = width * 0.13 + 0.12
        mesh.vertices[i * 2].co = center - lateral * (bank_widths[0] + margin)
        mesh.vertices[i * 2 + 1].co = center + lateral * (bank_widths[1] + margin)
        sections.append((center, lateral, bank_widths, distance))
    for face in mesh.polygons:
        face.use_smooth = True
    mesh.update()
    return water, sections


def shape_banks(terrain, channels):
    """Shape shallow shelves along the seeded waterlines, behind the water edges."""
    indexed_channels = []
    for sections in channels:
        tree = KDTree(len(sections))
        for index, (center, _, _, _) in enumerate(sections):
            tree.insert(Vector((center.x, center.y, 0)), index)
        tree.balance()
        indexed_channels.append((tree, sections))

    for vertex in terrain.data.vertices:
        point = vertex.co
        original = point.z
        targets = []
        for tree, sections in indexed_channels:
            _, index, separation = tree.find(Vector((point.x, point.y, 0)))
            if separation > 2.7:
                continue
            # Project onto an actual ribbon segment. A chord across both
            # neighbors cuts the corner and shifts abruptly at the next sample.
            closest = None
            for first in range(max(0, index - 1), min(index + 1, len(sections) - 1)):
                a, b = sections[first:first + 2]
                span = b[0].xy - a[0].xy
                if span.length_squared < 1.0e-8:
                    continue
                t = min(1.0, max(0.0, (point.xy - a[0].xy).dot(span) / span.length_squared))
                center = a[0].lerp(b[0], t)
                distance = (point.xy - center.xy).length_squared
                if closest is None or distance < closest[0]:
                    closest = (distance, a, b, t, center)
            if closest is None:
                continue
            distance, a, b, t, center = closest
            lateral = a[1].lerp(b[1], t).normalized()
            cross = (point - center).dot(lateral)
            side = int(cross >= 0)
            width = a[2][side] + t * (b[2][side] - a[2][side])
            offset = distance ** 0.5 - width
            # The gradual approach on the wet side creates shallow gravel shelves.
            if not -0.72 < offset < 0.73:
                if offset <= -0.72:
                    targets.append((offset, min(0.0, center.z - 0.28 - original)))
                continue
            influence = min(1.0, (offset + 0.72) / 0.44, (0.73 - offset) / 0.43)
            along = a[3] + t * (b[3] - a[3])
            influence *= min(1.0, along / 0.7, (sections[-1][3] - along) / 0.7)
            profile = center.z + offset * (0.37 if offset < 0 else 0.52)
            if influence > 0:
                targets.append((offset, (profile - original) * influence))
        if targets:
            # Let a shelf rise along dry land, tapering it away where the other
            # channel is wet so it cannot form a lip across the confluence.
            lowering = min(0.0, *(change for _, change in targets))
            raising = 0.0
            for index, (_, change) in enumerate(targets):
                if change <= 0.0:
                    continue
                for other, (offset, _) in enumerate(targets):
                    if other != index:
                        t = min(1.0, max(0.0, (offset + 0.2) / 0.4))
                        change *= t * t * (3.0 - 2.0 * t)
                raising = max(raising, change)
            point.z = original + lowering + raising
    terrain.data.update()


def build_waterways(terrain, group, shore_rng, shore_seed):
    bpy.context.view_layer.objects.active = terrain
    terrain.select_set(True)
    bpy.context.view_layer.update()
    spring_x = -12.25
    spring_y = stream_y(spring_x)
    hydroxus_rivers.register()
    try:
        river, river_banks = carve_channel(
            terrain, group, "Birch River", (river_x(23), 23), 2.65, 0.83, shore_rng,
        )
        stream, stream_banks = carve_channel(
            terrain, group, "Fern Stream", (spring_x, spring_y), 1.13, 0.48, shore_rng,
            join=lambda point: point.x >= river_x(point.y) - 0.84,
        )
        river_surface = BVHTree.FromObject(river, bpy.context.evaluated_depsgraph_get())
        # Keep the stream ribbon at the receiving water level inside the overlap.
        for vertex in stream.data.vertices:
            point = vertex.co
            hit, _, _, _ = river_surface.ray_cast((point.x, point.y, 25), (0, 0, -1))
            if hit is not None:
                point.z = max(point.z, hit.z - 0.004)
        stream.data.update()
        if len(river.data.vertices) < 200 or len(stream.data.vertices) < 50:
            raise RuntimeError("Hydroxus produced a shorter channel than the scene requires")
    finally:
        hydroxus_rivers.unregister()
    bpy.context.scene.cursor.location = (0, 0, 0)
    material = river.data.materials[0]
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    shader = nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (0.29, 0.38, 0.31, 1)
    shader.inputs["Transmission Weight"].default_value = 0.91
    shader.inputs["Roughness"].default_value = 0.19
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 5.5
    coordinates = nodes.new("ShaderNodeTexCoord")
    stretch = nodes.new("ShaderNodeVectorMath")
    stretch.operation = "MULTIPLY"
    stretch.inputs[1].default_value = (0.55, 2.2, 1.0)
    links.new(coordinates.outputs["Object"], stretch.inputs[0])
    links.new(stretch.outputs["Vector"], noise.inputs["Vector"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.018
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    for water in (river, stream):
        hydroxus_rivers.set_water_uv(water)
    banks = (river_banks, stream_banks)
    shape_banks(terrain, banks)
    outlet_section = min(stream_banks, key=lambda section: abs(section[0].x - (spring_x + 1.25)))
    spring = hydroxus_rivers.create_basin(
        terrain, group, "Alder Spring", (spring_x, spring_y), (1.45, 1.05),
        0.43, shore_seed + 61, level=outlet_section[0].z + 0.012, outlet=0, build_bed=False,
    )
    pond = hydroxus_rivers.create_basin(
        terrain, group, "Heather Pond", (6.95, 10.15), (2.42, 1.72),
        0.84, shore_seed + 109, build_bed=False,
    )
    spring_join = join_water_channels(stream, spring)
    stream["spring_join_center_blender_world"] = tuple(spring_join)
    join_water_channels(stream, river)
    spring["feeds"] = stream.name
    stream["water_source"] = spring.name
    return (river, stream, spring, pond), banks


def tint_shore(terrain, shore_rng):
    phase = shore_rng.uniform(0, tau)
    color = terrain.data.color_attributes["Trail tint"]
    for vertex in terrain.data.vertices:
        x, y, z = vertex.co
        if abs(x - river_x(y)) < 3.0:
            water_height = 0.065 * (y + 14) - 0.83 * 0.55
        elif x < river_x(y) and abs(y - stream_y(x)) < 1.8:
            water_height = (0.065 * (stream_y(x) + 14)
                            - 0.11 * (x - river_x(y)) - 0.48 * 0.55)
        else:
            continue
        above = z - water_height
        variation = (0.50 + 0.28 * sin(x * 1.4 + y * 0.9 + phase)
                     + 0.20 * sin(x * 5.8 + y * 2.3 + phase) * cos(y * 3.9))
        weight = max(0.0, 1.0 - abs(above - 0.04) / (0.24 + 0.13 * variation))
        weight *= 0.86
        shore = (0.52 + 0.23 * variation, 0.45 + 0.19 * variation, 0.32 + 0.16 * variation)
        original = color.data[vertex.index].color[:3]
        color.data[vertex.index].color = (
            *(old * (1 - weight) + new * weight for old, new in zip(original, shore)), 1,
        )


def outer_elevation(x, y):
    edge_x = max(-14, min(14, x))
    edge_y = min(23, y)
    distance = max(abs(x - edge_x), y - edge_y)
    transition = min(1, distance / 5)
    hills = 2.5 + 0.8 * sin(0.28 * x + 0.2 * y) + 0.45 * cos(0.44 * y - 0.2 * x)
    return (1 - transition) * elevation(edge_x, edge_y) + transition * hills


def add_outer_ground(group, material):
    for name, left, right, near, far in (
        ("North woodland floor", -28, 24, 22.96, 48),
        ("West woodland floor", -28, -13.96, -14, 22.96),
    ):
        columns, rows = 107, 85
        vertices = []
        for row in range(rows + 1):
            y = near + (far - near) * row / rows
            for column in range(columns + 1):
                x = left + (right - left) * column / columns
                vertices.append((x, y, outer_elevation(x, y) - 0.018))
        faces = []
        for row in range(rows):
            for column in range(columns):
                a = row * (columns + 1) + column
                b = a + columns + 1
                faces.append((a, a + 1, b + 1, b))
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        mesh.materials.append(material)
        color = mesh.color_attributes.new(name="Trail tint", type="FLOAT_COLOR", domain="POINT")
        mesh.color_attributes.active_color = color
        for index, (x, y, _) in enumerate(vertices):
            mottling = 0.5 + 0.5 * sin(1.8 * x + 0.67 * y) * sin(0.69 * x - 1.23 * y)
            color.data[index].color = (0.37 + 0.21 * mottling, 0.69 + 0.21 * mottling,
                                       0.48 + 0.15 * mottling, 1)
        uv = mesh.uv_layers.new(name="UVMap")
        for face in mesh.polygons:
            face.use_smooth = True
            for index in face.loop_indices:
                uv.data[index].uv = vertices[mesh.loops[index].vertex_index][:2]
        group.objects.link(bpy.data.objects.new(name, mesh))


def build(shore_seed, output, render=False, day_of_year=None, weather="clear",
          snow_hours=DEFAULT_SNOW_HOURS):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    rng = Random(43)
    shore_rng = Random(shore_seed)
    output.mkdir(parents=True, exist_ok=True)
    woodland.trail_x = trail_x
    woodland.edge = trail_edge
    woodland.height = elevation

    species_by_group = {
        "Canopy": ("Silver birch", "English oak", "Norway spruce", "European larch"),
        "Bank grasses": tuple(BANK_GRASSES),
        "Granite": ("Granite boulder", "Granite slab", "Granite cobble"),
        "Understory": ("Hard fern", "Bracken", "Common heather", "Wood melick",
                       "Sheep fescue", "English bluebell", "Oxeye daisy"),
    }
    groups = {}
    for name in ("Terrain", "Waterways", *species_by_group):
        groups[name] = bpy.data.collections.new(name)
        scene.collection.children.link(groups[name])
    woodland.ground(groups["Terrain"])
    terrain, = groups["Terrain"].objects
    waterways, shorelines = build_waterways(terrain, groups["Waterways"], shore_rng, shore_seed)
    tint_shore(terrain, shore_rng)
    hydroxus_rivers.dress_channel_beds(terrain, waterways, shore_seed, groups["Terrain"])
    for water in waterways:
        water["shore_seed"] = str(shore_seed)
    add_outer_ground(groups["Terrain"], terrain.data.materials[0])
    terrain_surface = BVHTree.FromObject(terrain, bpy.context.evaluated_depsgraph_get())
    water_surfaces = [
        BVHTree.FromObject(water, bpy.context.evaluated_depsgraph_get()) for water in waterways
    ]

    def surface_z(x, y):
        hit, _, _, _ = terrain_surface.ray_cast((x, y, 25), (0, 0, -1))
        return hit.z if hit is not None else outer_elevation(x, y)

    def water_depth(x, y, surfaces):
        ground_z = surface_z(x, y)
        depth = 0.0
        for surface in surfaces:
            hit, _, _, _ = surface.ray_cast((x, y, 25), (0, 0, -1))
            if hit is not None:
                depth = max(depth, hit.z - ground_z)
        return depth

    def in_water(x, y):
        return water_depth(x, y, water_surfaces) > 0.0

    models = {**woodland.MODELS, **BANK_GRASSES}
    meshes = {
        species: woodland.load_mesh(models[species])
        for group in species_by_group.values() for species in group
    }
    for species, mesh in meshes.items():
        mesh.name = species
    counts = Counter()

    def place(species, group, x, y, scale, sink=0.012, *, allow_water=False):
        if not allow_water and in_water(x, y):
            return
        counts[species] += 1
        obj = bpy.data.objects.new(f"{species} {counts[species]:02d}", meshes[species])
        groups[group].objects.link(obj)
        obj.location = (x, y, surface_z(x, y) - sink)
        obj.rotation_euler.z = rng.uniform(0, tau)
        if group == "Granite":
            obj.scale = (scale, scale * rng.uniform(0.65, 1.18), scale * rng.uniform(0.55, 0.95))
            obj.rotation_euler.x = rng.uniform(-0.18, 0.18)
        else:
            obj.scale = (scale, scale, scale * rng.uniform(0.9, 1.12))
        obj["asset"] = species
        obj["wind"] = group != "Granite"

    trees = [
        ("Silver birch", -5.1, -7.1), ("Silver birch", 1.9, -6.2),
        ("English oak", 6.2, -3.6), ("Norway spruce", -9.3, -4.7),
        ("European larch", 8.9, 1.4), ("Silver birch", -8.0, 0.6),
        ("Silver birch", -9.1, 5.1), ("Silver birch", -6.5, 8.5),
        ("Silver birch", -4.2, 10.8), ("English oak", -8.5, 12.1),
        ("Norway spruce", 8.6, 8.0), ("Silver birch", 4.8, 11.8),
        ("European larch", 7.7, 14.7), ("Silver birch", 2.6, 16.5),
        ("Norway spruce", -6.6, 17.4), ("Norway spruce", -0.3, 19.3),
        ("Silver birch", -10.2, 17.4), ("European larch", 10.3, 18.4),
    ]
    rocks = [
        ("Granite boulder", 5.1, 2.8, 1.9), ("Granite slab", 5.7, 4.1, 1.7),
        ("Granite boulder", 6.8, 3.7, 2.4), ("Granite slab", 6.6, 5.0, 1.55),
        ("Granite boulder", 5.2, 5.6, 1.25), ("Granite slab", 4.4, 5.1, 1.05),
        ("Granite boulder", -4.7, -4.9, 0.95),
    ]
    for species, x, y in trees:
        place(species, "Canopy", x, y, rng.uniform(0.84, 1.18), 0.045)
    # Close the distant sightline with uneven, overlapping layers of canopy.
    for row, y in enumerate((15.0, 18.5, 21.4)):
        for x in range(-12, 14, 3):
            if abs(x - trail_x(y)) < 2:
                continue
            species = ("Norway spruce", "Silver birch", "European larch")[(x // 3 + row) % 3]
            place(species, "Canopy", x + rng.uniform(-0.7, 0.7),
                  y + rng.uniform(-0.8, 0.8), rng.uniform(0.83, 1.29), 0.05)
    backdrop_rng = Random(86)
    for y in range(-6, 43, 4):
        for x in range(-26, 20, 4):
            if x >= -14 and y <= 23:
                continue
            species = backdrop_rng.choice(("Norway spruce", "European larch", "Silver birch"))
            place(species, "Canopy", x + backdrop_rng.uniform(-0.9, 0.9),
                  y + backdrop_rng.uniform(-0.9, 0.9), backdrop_rng.uniform(0.76, 1.31), 0.08)
    for species, x, y, scale in rocks:
        place(species, "Granite", x, y, scale, 0.13 * scale)

    def clear(x, y):
        return (
            abs(x - trail_x(y)) > trail_edge(y) + 0.15
            and all((x - a) ** 2 + (y - b) ** 2 > 0.55 ** 2 for _, a, b in trees)
            and all((x - a) ** 2 + (y - b) ** 2 > (0.48 * s) ** 2 for _, a, b, s in rocks)
        )

    patches = [
        ("English bluebell", -3.6, -5.8, 26),
        ("English bluebell", -3.0, -1.1, 34),
        ("English bluebell", -4.1, 4.2, 35),
        ("English bluebell", -5.1, 7.3, 30),
        ("Oxeye daisy", -3.7, 2.2, 24),
        ("Oxeye daisy", -2.0, 6.2, 20),
        ("Common heather", 3.8, 3.8, 13),
        ("Hard fern", 4.0, 1.5, 16),
        ("Hard fern", 4.2, 6.7, 17),
        ("Bracken", 6.6, 7.1, 15),
        ("Bracken", -6.8, 4.8, 14),
    ]
    for species, center_x, center_y, count in patches:
        for _ in range(count):
            x = center_x + rng.uniform(-1.05, 1.05)
            y = center_y + rng.uniform(-1.15, 1.15)
            if clear(x, y):
                place(species, "Understory", x, y, rng.uniform(0.7, 1.22))

    for index in range(340):
        y = rng.uniform(-11.5, 18.5)
        side = 1 if index % 2 else -1
        x = trail_x(y) + side * (trail_edge(y) + rng.uniform(0.13, 6.8))
        if clear(x, y):
            species = "Wood melick" if index % 5 == 0 else "Sheep fescue"
            place(species, "Understory", x, y, rng.uniform(0.52, 1.22))
    for _ in range(44):
        x, y = rng.uniform(3.2, 8.2), rng.uniform(1.2, 7.9)
        if clear(x, y):
            place("Granite cobble", "Granite", x, y, rng.uniform(0.35, 1.1), 0.025)

    # Scatter gravel in asymmetric bars, with gaps and clusters of vegetation.
    for sections in shorelines:
        for side, direction in enumerate((-1, 1)):
            patch_phase = shore_rng.uniform(0, tau)
            for center, lateral, widths, distance in sections:
                if distance < 0.5 or distance > sections[-1][3] - 0.65:
                    continue
                patch = 0.50 + 0.30 * sin(0.72 * distance + patch_phase)
                patch += 0.20 * sin(1.83 * distance - patch_phase)
                if shore_rng.random() > 0.12 + 0.70 * patch:
                    continue
                outward = lateral * direction
                edge = center + outward * widths[side]
                for _ in range(shore_rng.randint(1, 3)):
                    position = edge + outward * shore_rng.uniform(-0.31, 0.58)
                    x = position.x + shore_rng.uniform(-0.20, 0.20)
                    y = position.y + shore_rng.uniform(-0.20, 0.20)
                    size = shore_rng.uniform(0.25, 0.79) ** 2
                    place("Granite cobble", "Granite", x, y, size, 0.007, allow_water=True)
                if patch > 0.56 and shore_rng.random() < 0.48:
                    point = edge + outward * shore_rng.uniform(0.54, 1.25)
                    species = "Hard fern" if shore_rng.random() < 0.40 else "Wood melick"
                    place(species, "Understory", point.x, point.y, shore_rng.uniform(0.42, 0.86))

    # Wet margins favor clusters of grass and ferns with scattered exposed stones.
    for water in waterways[2:]:
        center = water.data.vertices[0].co
        bank_rng = Random(int(water["bed_seed"]))
        for vertex in list(water.data.vertices)[1::2]:
            offset = vertex.co - center
            point = center + offset * bank_rng.uniform(0.86, 1.14)
            if bank_rng.random() < 0.30:
                place("Granite cobble", "Granite", point.x, point.y,
                      bank_rng.uniform(0.26, 0.69), allow_water=True)
            else:
                species = bank_rng.choice(("Hard fern", "Wood melick", "Wood melick", "Common heather"))
                place(species, "Understory", point.x, point.y, bank_rng.uniform(0.64, 1.08))
    spring = waterways[2].data.vertices[0].co
    for dx, dy, scale in ((-1.07, -0.35, 0.82), (-0.98, 0.42, 0.67), (-0.64, 0.63, 0.52)):
        place("Granite boulder", "Granite", spring.x + dx, spring.y + dy, scale,
              0.07, allow_water=True)

    for y in (-7.1, -0.5, 8.8, 12.6):
        place("Granite boulder", "Granite", river_x(y) + 0.74, y, rng.uniform(0.65, 0.98),
              0.02, allow_water=True)

    # Use the same bank sections as the water and gravel. Place plants in patches,
    # checking the actual meshes after carving and joining the waterways.
    bank_rng = Random(shore_seed ^ 0x29365)
    species_zones = (
        ("Floating sweet-grass", (-.30, -.025), (.72, 1.02), .55),
        ("Creeping bent", (.12, .46), (.65, 1.25), .35),
        ("Tufted hairgrass", (.43, 1.05), (.52, .94), .94),
    )
    for channel, sections in enumerate(shorelines):
        for side, direction in enumerate((-1, 1)):
            phase = bank_rng.uniform(0, tau)
            for species, offsets, scales, spacing in species_zones:
                next_distance = .8
                for center, lateral, widths, distance in sections:
                    if distance < next_distance or distance > sections[-1][3] - .85:
                        continue
                    next_distance = distance + spacing * bank_rng.uniform(.69, 1.43)
                    if sin(1.4 * distance + phase) < -.48:
                        continue
                    outward = lateral * direction
                    along = Vector((outward.y, -outward.x, 0))
                    point = center + outward * (widths[side] + bank_rng.uniform(*offsets))
                    point += along * bank_rng.uniform(-.13, .13)
                    x, y = point.x, point.y
                    if not clear(x, y):
                        continue
                    shallow = species == "Floating sweet-grass"
                    if shallow and not .005 < water_depth(x, y, (water_surfaces[channel],)) < .12:
                        continue
                    place(species, "Bank grasses", x, y, bank_rng.uniform(*scales),
                          allow_water=shallow)

    if day_of_year is not None:
        add_litter(scene, groups["Canopy"].objects, surface_z, in_water, day_of_year, shore_seed)
        apply_growth(meshes.values(), day_of_year)
        apply_blender(bpy.data.materials, day_of_year)
        scene["day_of_year"] = day_of_year
    snow = apply_ground(terrain, weather, lambda x, y: water_depth(x, y, water_surfaces),
                        list(groups["Canopy"].objects), snow_hours)
    bpy.ops.export_scene.gltf(
        filepath=str(output / "birch-glade.glb"), export_format="GLB",
        export_tangents=True, export_extras=True, export_vertex_color="ACTIVE",
        export_all_vertex_colors=False,
    )
    scene, (trail_camera, overview) = woodland.setup_studio()
    camera_y = -5.7
    camera_x = -1.62
    trail_camera.location = (camera_x, camera_y, surface_z(camera_x, camera_y) + 1.85)
    woodland.point_at(trail_camera, (-5.2, 4.8, 0.85))
    trail_camera.data.lens = 25
    overview.location = (3, -15, 28)
    woodland.point_at(overview, (0, 3, 0))
    overview.data.ortho_scale = 32
    for water, offset, lens in (
        (waterways[2], (3.1, -2.7, 2.2), 31),
        (waterways[3], (-3.2, -4.1, 2.75), 35),
    ):
        center = water.data.vertices[0].co
        camera_data = bpy.data.cameras.new(f"{water.name} view")
        camera_data.lens = lens
        camera = bpy.data.objects.new(camera_data.name, camera_data)
        scene.collection.objects.link(camera)
        camera.location = center + Vector(offset)
        woodland.point_at(camera, center)
    scene.cycles.use_denoising = False
    scene.cycles.samples = 28
    scene.cycles.adaptive_threshold = 0.045
    sun = bpy.data.objects["Warm morning sun"]
    sun.location = (-7, 4, 9)
    woodland.point_at(sun, (0, 0, 0))
    sun.data.energy = 2.75
    sun.data.color = (1.0, 0.94, 0.85)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.47
    apply_atmosphere(scene, sun, weather, shore_seed)
    animate_accumulation(scene, snow, snow_hours)
    scene["weather"] = weather
    if snow is not None:
        scene["snow_hours"] = snow_hours
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 680
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_perspective = "CAMERA"
    scene.render.filepath = "//birch-glade.png"
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "birch-glade.blend"))
    print(f"Birch Glade placements: {dict(counts)}", flush=True)
    if render:
        scene.render.filepath = str(output / "birch-glade.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    seeds = parser.add_mutually_exclusive_group()
    seeds.add_argument("--shore-seed", type=int, default=2741)
    seeds.add_argument("--random-shore", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--day-of-year", type=float, help="Snapshot day on a 365-day calendar")
    parser.add_argument("--weather", choices=PRESETS, default="clear")
    parser.add_argument("--snow-hours", type=float, default=DEFAULT_SNOW_HOURS,
                        help="Hours of snowfall to export (0 to 24, default 12)")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if args.day_of_year is not None and not isfinite(args.day_of_year):
        parser.error("--day-of-year must be finite")
    if not 0 <= args.snow_hours <= FULL_SNOW_HOURS:
        parser.error("--snow-hours must be between 0 and 24")
    seed = SystemRandom().randrange(2**32) if args.random_shore else args.shore_seed
    print(f"Shore seed: {seed}", flush=True)
    output = args.output_dir
    if output is None:
        output = OUTPUT
        if args.day_of_year is not None or args.weather != "clear":
            name = f"day-{args.day_of_year:g}" if args.day_of_year is not None else "summer"
            if args.weather != "clear":
                name += f"-{args.weather}"
            if args.weather == "snow":
                name += f"-{args.snow_hours:g}h"
            output = OUTPUT / "variants" / name
    build(seed, output.resolve(), args.render, args.day_of_year, args.weather, args.snow_hours)

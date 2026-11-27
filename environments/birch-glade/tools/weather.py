"""Authored surface weather and looping Blender precipitation for Birch Glade."""
from math import cos, sin, tau
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory

import bpy
import numpy as np
from mathutils import Vector

from build_pine import write_png

PRESETS = ("clear", "rain", "snow")
FULL_SNOW_HOURS = 24.0
DEFAULT_SNOW_HOURS = 12.0


def crystal_maps():
    """A tile of randomly oriented ice facets amid rougher snow grains."""
    rng = np.random.default_rng(6301)
    size, cells = 512, 112
    y, x = (np.mgrid[:size, :size] + .5) * (cells / size)
    i, j = x.astype(int), y.astype(int)
    seed = rng.uniform(.12, .88, (cells, cells, 2))
    nearest = np.full_like(x, np.inf)
    second = nearest.copy()
    cell_i, cell_j = i.copy(), j.copy()
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            a, b = (i+dx) % cells, (j+dy) % cells
            offset = seed[b, a]
            d = (i+dx+offset[..., 0]-x)**2 + (j+dy+offset[..., 1]-y)**2
            better = d < nearest
            second = np.minimum(second, np.maximum(nearest, d))
            nearest = np.minimum(nearest, d)
            cell_i = np.where(better, a, cell_i)
            cell_j = np.where(better, b, cell_j)

    angle = rng.uniform(0, tau, (cells, cells))[cell_j, cell_i]
    slope = rng.uniform(.045, .52, (cells, cells))[cell_j, cell_i]
    facet = np.clip((np.sqrt(second)-np.sqrt(nearest)) / .22, 0, 1)
    xy = slope * (.5 + .5*facet)
    normal = np.stack((xy*np.cos(angle), xy*np.sin(angle), np.sqrt(1-xy**2)), axis=-1)
    ice = (rng.random((cells, cells))[cell_j, cell_i] < .17) * facet
    roughness = .67 + .16*(1-facet) - .55*ice
    orm = np.stack((np.ones_like(roughness), roughness, np.zeros_like(roughness)), axis=-1)
    return normal*.5+.5, orm


def add_crystal_maps(material, uv_name):
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes.get("Principled BSDF")
    normal_pixels, orm_pixels = crystal_maps()
    textures = []
    with TemporaryDirectory(prefix="birch-snow-") as scratch:
        for name, pixels in (("snow-crystal-normal", normal_pixels), ("snow-crystal-orm", orm_pixels)):
            path = Path(scratch) / f"{name}.png"
            write_png(path, pixels)
            texture = nodes.new("ShaderNodeTexImage")
            texture.label = name
            texture.image = bpy.data.images.load(str(path))
            texture.image.colorspace_settings.name = "Non-Color"
            texture.image.pack()
            texture.image.filepath = "//" + path.name
            textures.append(texture)

    normal = nodes.new("ShaderNodeNormalMap")
    normal.uv_map = uv_name
    links.new(textures[0].outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    channels = nodes.new("ShaderNodeSeparateColor")
    links.new(textures[1].outputs["Color"], channels.inputs["Color"])
    links.new(channels.outputs["Green"], shader.inputs["Roughness"])
    links.new(channels.outputs["Blue"], shader.inputs["Metallic"])


def snow_cutoff(hours):
    return 1.0 - .98 * (hours / FULL_SNOW_HOURS)


def settled_depth(readiness, thickness, hours):
    fraction = hours / FULL_SNOW_HOURS
    # Taper to the exposed ground at the edge of each young patch.
    edge = (readiness - snow_cutoff(hours)) / (.025 + .16*(1-fraction))
    edge = max(0.0, min(1.0, edge))
    return thickness * fraction * edge*edge*(3-2*edge)


def snow_material(hours):
    material = bpy.data.materials.new("Accumulated snow")
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes.get("Principled BSDF")
    tint = nodes.new("ShaderNodeVertexColor")
    tint.layer_name = "Snow coverage"
    cutoff = nodes.new("ShaderNodeMath")
    cutoff.operation = "GREATER_THAN"
    cutoff.inputs[1].default_value = snow_cutoff(hours)
    links.new(tint.outputs["Color"], shader.inputs["Base Color"])
    links.new(tint.outputs["Alpha"], cutoff.inputs[0])
    links.new(cutoff.outputs[0], shader.inputs["Alpha"])
    add_crystal_maps(material, "Snow crystals")
    return material, cutoff.inputs[1]


def cover_mesh(name, positions, faces, readiness, material, tile_size):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(positions, [], faces)
    uv = mesh.uv_layers.new(name="Snow crystals")
    for loop in mesh.loops:
        x, y, _ = positions[loop.vertex_index]
        uv.data[loop.index].uv = (x / tile_size, y / tile_size)
    colors = mesh.color_attributes.new(name="Snow coverage", type="FLOAT_COLOR", domain="POINT")
    for sample, alpha in zip(colors.data, readiness):
        shade = .78 + .20*alpha
        sample.color = (.83*shade, .90*shade, shade, alpha)
    mesh.color_attributes.active_color = colors
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    mesh.materials.append(material)
    mesh.update()
    return mesh


def apply_ground(terrain, mode, water_depth, canopy=(), hours=DEFAULT_SNOW_HOURS):
    """Author the selected snapshot and return the data needed to animate its snowfall."""
    if mode == "clear":
        return None
    source = terrain.data
    if mode == "rain":
        tint = source.color_attributes.get("Trail tint")
        if tint is not None:
            for sample in tint.data:
                red, green, blue, alpha = sample.color
                sample.color = (red*.69, green*.72, blue*.76, alpha)
        return None

    material, cutoff = snow_material(hours)
    readiness, base, depth = [], [], []
    for vertex in source.vertices:
        x, y, z = vertex.co
        water = water_depth(x, y)
        patch = .63 + .21*sin(1.6*x + .6*y + .7*sin(y))
        patch += .14*sin(2.9*y - 1.9*x) + .08*cos(5.2*x + 4.4*y)
        slope = max(0.0, min(1.0, (vertex.normal.z-.48)/.5))
        texture = max(0.0, min(1.0, patch * (.43 + .57*slope)))
        if water > 0:
            # Only a narrow shelf beside the shallowest margins can collect snow.
            readiness.append(.16*(1-water/.11) if water < .085 else 0.0)
            base.append(z + water + .008)
            depth.append(.015)
        else:
            close_to_stream = any(water_depth(x+dx, y+dy) > 0
                                  for dx,dy in ((.42,0),(-.42,0),(0,.42),(0,-.42)))
            readiness.append(.045 + .94*texture)
            base.append(z + .012)
            depth.append(.12 + .08*texture if close_to_stream else .43 + .04*texture)

    positions, faces, opacity, thickness = [], [], [], []
    used = {}
    for polygon in source.polygons:
        if all(readiness[i] == 0.0 for i in polygon.vertices):
            continue
        face = []
        for index in polygon.vertices:
            if index not in used:
                used[index] = len(positions)
                x, y, _ = source.vertices[index].co
                positions.append((x, y, base[index] + settled_depth(readiness[index], depth[index], hours)))
                opacity.append(readiness[index])
                thickness.append(depth[index])
            face.append(used[index])
        faces.append(face)

    mesh = cover_mesh("Forest floor snow", positions, faces, opacity, material, .42)
    cover = bpy.data.objects.new("Forest floor snow", mesh)
    terrain.users_collection[0].objects.link(cover)
    surfaces = [(cover, thickness)]
    bpy.context.view_layer.update()

    # Reuse branch caps for every instance of a source tree mesh.
    branches = {}
    for tree in canopy:
        if tree.data not in branches:
            branches[tree.data] = branch_snow(tree.data, material, hours)
        prototype = branches[tree.data]
        if prototype is None:
            continue
        branch_mesh, buildup = prototype
        obj = bpy.data.objects.new(f"{tree.name} snow", branch_mesh)
        tree.users_collection[0].objects.link(obj)
        obj.matrix_world = tree.matrix_world.copy()
        if branch_mesh.users == 1:
            surfaces.append((obj, buildup))
    return cutoff, surfaces


def branch_snow(source, material, hours):
    wood = {i for i, slot in enumerate(source.materials) if slot and slot.name.endswith(" Bark")}
    positions, faces, readiness, thickness = [], [], [], []
    used = {}
    for face in source.polygons:
        if face.material_index not in wood or face.normal.z < .25:
            continue
        indices = []
        for index in face.vertices:
            if index not in used:
                vertex = source.vertices[index]
                x, y, z = vertex.co
                top = max(0.0, min(1.0, (vertex.normal.z-.22)/.68))
                depth = .035 + .055*top
                used[index] = len(positions)
                alpha = .06 + .82*top
                positions.append((x, y, z+.009 + settled_depth(alpha, depth, hours)))
                readiness.append(alpha)
                thickness.append(depth)
            indices.append(used[index])
        faces.append(indices)
    if not faces:
        return None
    return cover_mesh(f"{source.name} branch snow", positions, faces, readiness, material, .34), thickness


def animate_accumulation(scene, snow, hours):
    """Animate the Blender scene after exporting the static game snapshot."""
    if snow is None:
        return
    cutoff, surfaces = snow
    stages = sorted({0.0, 6.0, 12.0, 18.0, FULL_SNOW_HOURS, hours})
    end_frame = 1 + 6*FULL_SNOW_HOURS
    for stage in (0, FULL_SNOW_HOURS):
        cutoff.default_value = snow_cutoff(stage)
        cutoff.keyframe_insert(data_path="default_value", frame=1+6*stage)
    actions = [cutoff.id_data.animation_data.action]
    for obj, thickness in surfaces:
        alpha = [sample.color[3] for sample in obj.data.color_attributes["Snow coverage"].data]
        for vertex, readiness, depth in zip(obj.data.vertices, alpha, thickness):
            vertex.co.z -= settled_depth(readiness, depth, hours)
        obj.shape_key_add(name="Bare surface")
        for index, stage in enumerate(stages[1:], 1):
            layer = obj.shape_key_add(name=f"{stage:g} hours of snow")
            for vertex, readiness, depth in zip(layer.data, alpha, thickness):
                vertex.co.z += settled_depth(readiness, depth, stage)
            for key_index in range(index-1, min(len(stages), index+2)):
                layer.value = float(key_index == index)
                layer.keyframe_insert(data_path="value", frame=1+6*stages[key_index])
            layer.value = 0.0
        actions.append(obj.data.shape_keys.animation_data.action)
    for action in actions:
        for curve in action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = "LINEAR"
    scene.frame_end = int(end_frame)
    frame = 1 + 6*hours
    scene.frame_set(int(frame), subframe=frame-int(frame))


def apply_atmosphere(scene, sun, mode, seed):
    """Change the light and animate two repeating batches of nearby particles."""
    if mode == "clear":
        return
    snow = mode == "snow"
    sun.data.energy *= .49 if snow else .32
    sun.data.angle = .25
    sun.data.color = (.82, .88, 1.0) if snow else (.73, .81, .93)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value *= .86
    rain_or_snow = "Snowflakes" if snow else "Rain streaks"
    rng = Random(seed ^ 0xBE318)
    drift = Vector((1.5, -.50, -8.0) if snow else (1.15, -.45, -8.0))
    horizontal = Vector((1.0, 0.0, 0.0))
    frame_span = 132 if snow else 27
    vertices, faces = [], []
    origin = scene.camera.location
    for _ in range(1300 if snow else 1680):
        point = origin + Vector((rng.uniform(-6, 6), rng.uniform(-3, 13), rng.uniform(-3.5, 4.5)))
        long_axis = drift.normalized() * (rng.uniform(.004, .013) if snow else rng.uniform(.045, .15))
        edge = horizontal * (rng.uniform(.004, .012) if snow else rng.uniform(.0007, .0016))
        start = len(vertices)
        vertices.extend((point - long_axis - edge, point - long_axis + edge,
                         point + long_axis + edge, point + long_axis - edge))
        faces.append((start, start+1, start+2, start+3))
    mesh = bpy.data.meshes.new(rain_or_snow)
    mesh.from_pydata(vertices, [], faces)
    if snow:
        uv = mesh.uv_layers.new(name="Flake UV")
        for face in mesh.polygons:
            for loop, point in zip(face.loop_indices, ((0, 0), (1, 0), (1, 1), (0, 1))):
                uv.data[loop].uv = point
    material = bpy.data.materials.new(rain_or_snow)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes.get("Principled BSDF")
    color = (.85, .91, 1.0, 1.0) if snow else (.54, .65, .78, 1.0)
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Emission Color"].default_value = color
    shader.inputs["Emission Strength"].default_value = .30 if snow else .16
    translucent = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = .40
    if snow:
        # Feather the edges of each small flake, including ones close to camera.
        coordinates = nodes.new("ShaderNodeTexCoord")
        distance = nodes.new("ShaderNodeVectorMath")
        distance.operation = "DISTANCE"
        distance.inputs[1].default_value = (.5, .5, 0)
        fade = nodes.new("ShaderNodeMapRange")
        fade.interpolation_type = "SMOOTHSTEP"
        fade.inputs["From Min"].default_value = .15
        fade.inputs["From Max"].default_value = .5
        fade.inputs["To Min"].default_value = .9
        fade.inputs["To Max"].default_value = 0.0
        links.new(coordinates.outputs["UV"], distance.inputs[0])
        links.new(distance.outputs["Value"], fade.inputs["Value"])
        links.new(fade.outputs["Result"], mix.inputs[0])
    links.new(translucent.outputs[0], mix.inputs[1])
    links.new(shader.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], nodes.get("Material Output").inputs["Surface"])
    mesh.materials.append(material)
    group = bpy.data.collections.new("Precipitation")
    scene.collection.children.link(group)
    for layer in range(2):
        obj = bpy.data.objects.new(rain_or_snow, mesh)
        group.objects.link(obj)
        obj.visible_shadow = False
        obj.location = -layer * drift
        obj.keyframe_insert(data_path="location", frame=1)
        obj.location += drift
        obj.keyframe_insert(data_path="location", frame=1+frame_span)
        for curve in obj.animation_data.action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = "LINEAR"
            curve.modifiers.new("CYCLES")
    scene.frame_set(1)

"""Authored surface weather and looping Blender precipitation for Birch Glade."""
from math import cos, sin, tau
from random import Random

import bpy
from mathutils import Vector

PRESETS = ("clear", "rain", "snow")


def apply_ground(terrain, mode, in_water):
    """Darken loam in rain or lay a cutout cover over dry, gentle slopes."""
    if mode == "clear":
        return
    source = terrain.data
    if mode == "rain":
        for attr in source.color_attributes:
            if attr.name != "Trail tint":
                continue
            for sample in attr.data:
                red, green, blue, alpha = sample.color
                sample.color = (red * .69, green * .72, blue * .76, alpha)
        return

    coverage = []
    for vertex in source.vertices:
        x, y, z = vertex.co
        patches = .64 + .22*sin(1.6*x + .6*y + .7*sin(y))
        patches += .15*sin(2.9*y - 1.9*x) + .09*cos(5.2*x + 4.4*y)
        slope = max(0.0, min(1.0, (vertex.normal.z-.62)/.35))
        coverage.append(0.0 if in_water(x, y) else max(0.0, min(1.0, patches*slope)))

    positions, faces, opacity = [], [], []
    used = {}
    for polygon in source.polygons:
        if max(coverage[i] for i in polygon.vertices) <= .5:
            continue
        face = []
        for index in polygon.vertices:
            if index not in used:
                used[index] = len(positions)
                x, y, z = source.vertices[index].co
                positions.append((x, y, z+.015))
                opacity.append(coverage[index])
            face.append(used[index])
        faces.append(face)

    mesh = bpy.data.meshes.new("Snow cover")
    mesh.from_pydata(positions, [], faces)
    colors = mesh.color_attributes.new(name="Snow coverage", type="FLOAT_COLOR", domain="POINT")
    for index, sample in enumerate(colors.data):
        shade = .77 + .21*opacity[index]
        sample.color = (.83*shade, .90*shade, shade, opacity[index])
    mesh.color_attributes.active_color = colors
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    material = bpy.data.materials.new("Ground snow")
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes.get("Principled BSDF")
    shader.inputs["Roughness"].default_value = .92
    tint = nodes.new("ShaderNodeVertexColor")
    tint.layer_name = colors.name
    cutoff = nodes.new("ShaderNodeMath")
    cutoff.operation = "GREATER_THAN"
    cutoff.inputs[1].default_value = .50
    links.new(tint.outputs["Color"], shader.inputs["Base Color"])
    links.new(tint.outputs["Alpha"], cutoff.inputs[0])
    links.new(cutoff.outputs[0], shader.inputs["Alpha"])
    mesh.materials.append(material)
    cover = bpy.data.objects.new("Snow cover", mesh)
    terrain.users_collection[0].objects.link(cover)


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

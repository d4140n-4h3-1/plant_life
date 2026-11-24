"""Render a ten-second water-flow preview from the saved Birch Glade scene."""
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def animate_water(water, speed, fps):
    if water.data.uv_layers.get("FlowUV") is None:
        raise RuntimeError(f"{water.name} needs FlowUV")
    material = water.data.materials[0].copy()
    material.name = f"{water.name} animated preview"
    water.data.materials[0] = material
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    shader = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
    noise = next(node for node in nodes if node.type == "TEX_NOISE")
    bump = next(node for node in nodes if node.type == "BUMP")

    uv = nodes.new("ShaderNodeUVMap")
    uv.uv_map = "FlowUV"
    advection = nodes.new("ShaderNodeVectorMath")
    advection.operation = "ADD"
    links.new(uv.outputs["UV"], advection.inputs[0])
    offset = advection.inputs[1].driver_add("default_value", 0).driver
    offset.expression = f"-(frame - 1) * {speed / fps!r}"

    stretch = nodes.new("ShaderNodeVectorMath")
    stretch.operation = "MULTIPLY"
    stretch.inputs[1].default_value = (1.8, 0.44, 1.0)
    links.new(advection.outputs["Vector"], stretch.inputs[0])
    links.new(stretch.outputs["Vector"], noise.inputs["Vector"])
    noise.inputs["Scale"].default_value = 3.0
    bump.inputs["Strength"].default_value = 0.46
    bump.inputs["Distance"].default_value = 0.032

    shades = nodes.new("ShaderNodeValToRGB")
    shades.color_ramp.elements[0].position = 0.27
    shades.color_ramp.elements[0].color = (0.13, 0.26, 0.23, 1.0)
    shades.color_ramp.elements[1].position = 0.72
    shades.color_ramp.elements[1].color = (0.39, 0.54, 0.46, 1.0)
    links.new(noise.outputs["Fac"], shades.inputs["Fac"])
    links.new(shades.outputs["Color"], shader.inputs["Base Color"])
    shader.inputs["Transmission Weight"].default_value = 0.78
    shader.inputs["Roughness"].default_value = 0.16


def render_preview(frames):
    frames.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    fps = 8
    animate_water(bpy.data.objects["Birch River"], speed=0.68, fps=fps)
    animate_water(bpy.data.objects["Fern Stream"], speed=1.05, fps=fps)

    camera = scene.camera
    start = (-1.75, -5.4, 2.85)
    target = (-5.15, 2.45, 0.46)
    for frame, position, look_at in (
        (1, start, target),
        (17, start, target),
        (48, (-1.35, -2.5, 3.65), (-5.66, 4.3, 0.62)),
        (80, (-1.42, 0.8, 4.55), (-6.85, 5.45, 0.72)),
    ):
        camera.location = position
        camera.rotation_euler = (Vector(look_at) - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.keyframe_insert(data_path="location", frame=frame)
        camera.keyframe_insert(data_path="rotation_euler", frame=frame)
    camera.data.lens = 27
    scene.frame_start, scene.frame_end = 1, fps * 10
    scene.render.fps = fps
    scene.render.use_persistent_data = True
    scene.render.resolution_x, scene.render.resolution_y = 448, 288
    scene.render.resolution_percentage = 100
    scene.cycles.samples = 4
    scene.cycles.use_animated_seed = False
    scene.view_settings.exposure = 0.6
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(frames / "frame_")
    bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    render_preview(Path(sys.argv[sys.argv.index("--") + 1]).resolve())

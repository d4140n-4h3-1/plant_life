"""Render a ten-second water-flow preview from the saved Birch Glade scene."""
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def animate_water(water, speed, fps, junction):
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

    position = nodes.new("ShaderNodeNewGeometry").outputs["Position"]
    drift = nodes.new("ShaderNodeVectorMath")
    drift.operation = "ADD"
    links.new(position, drift.inputs[0])
    shared_offset = drift.inputs[1].driver_add("default_value", 1).driver
    # The receiving river moves toward negative Blender Y.
    shared_offset.expression = f"(frame - 1) * {0.75 / fps!r}"
    shared_noise = nodes.new("ShaderNodeTexNoise")
    shared_noise.inputs["Scale"].default_value = 3.6
    links.new(drift.outputs["Vector"], shared_noise.inputs["Vector"])

    distance = nodes.new("ShaderNodeVectorMath")
    distance.operation = "DISTANCE"
    links.new(position, distance.inputs[0])
    distance.inputs[1].default_value = junction
    weight = nodes.new("ShaderNodeMapRange")
    weight.interpolation_type = "SMOOTHSTEP"
    weight.inputs["From Min"].default_value = 0.78
    weight.inputs["From Max"].default_value = 2.2
    weight.inputs["To Min"].default_value = 1.0
    weight.inputs["To Max"].default_value = 0.0
    links.new(distance.outputs["Value"], weight.inputs["Value"])
    surface = nodes.new("ShaderNodeMixRGB")
    links.new(weight.outputs["Result"], surface.inputs[0])
    links.new(noise.outputs["Fac"], surface.inputs[1])
    links.new(shared_noise.outputs["Fac"], surface.inputs[2])
    noise.inputs["Scale"].default_value = 3.0
    links.new(surface.outputs["Color"], bump.inputs["Height"])
    bump.inputs["Strength"].default_value = 0.31
    bump.inputs["Distance"].default_value = 0.032

    shades = nodes.new("ShaderNodeValToRGB")
    shades.color_ramp.elements[0].position = 0.27
    shades.color_ramp.elements[0].color = (0.13, 0.26, 0.23, 1.0)
    shades.color_ramp.elements[1].position = 0.72
    shades.color_ramp.elements[1].color = (0.39, 0.54, 0.46, 1.0)
    links.new(surface.outputs["Color"], shades.inputs["Fac"])
    links.new(shades.outputs["Color"], shader.inputs["Base Color"])
    shader.inputs["Transmission Weight"].default_value = 0.78
    shader.inputs["Roughness"].default_value = 0.16


def render_preview(frames, test_frame=None):
    frames.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    fps = 6
    river = bpy.data.objects["Birch River"]
    stream = bpy.data.objects["Fern Stream"]
    junction = stream.matrix_world @ Vector(stream["join_center_local"])
    animate_water(river, speed=0.68, fps=fps, junction=junction)
    animate_water(stream, speed=1.05, fps=fps, junction=junction)

    camera = scene.camera
    start = (-1.95, -3.5, 2.88)
    target = (-5.05, 3.2, 0.58)
    for frame, position, look_at in (
        (1, start, target),
        (7, start, target),
        (34, (-2.0, -0.8, 3.45), (-5.74, 4.75, 0.75)),
        (60, (-2.46, 2.6, 3.50), (-6.64, 5.43, 0.86)),
    ):
        camera.location = position
        camera.rotation_euler = (Vector(look_at) - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.keyframe_insert(data_path="location", frame=frame)
        camera.keyframe_insert(data_path="rotation_euler", frame=frame)
    camera.data.lens = 24
    scene.frame_start, scene.frame_end = 1, fps * 10
    scene.render.fps = fps
    scene.render.use_persistent_data = True
    scene.render.resolution_x, scene.render.resolution_y = 512, 320
    scene.render.resolution_percentage = 100
    scene.cycles.samples = 8
    scene.cycles.use_animated_seed = False
    scene.view_settings.exposure = 0.6
    for layer in scene.view_layers:
        layer.cycles.denoising_store_passes = True
    scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    scene.render.image_settings.color_depth = "16"
    scene.render.filepath = str(frames / "frame_")
    if test_frame is None:
        bpy.ops.render.render(animation=True)
    else:
        scene.frame_set(test_frame)
        scene.render.filepath = str(frames / f"frame_{test_frame:04d}.exr")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    render_preview(Path(args[0]).resolve(), int(args[1]) if len(args) > 1 else None)

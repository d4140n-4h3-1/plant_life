"""Build low-growing, alpha-masked woodland grass clumps in Blender 4.3."""
from math import cos, pi, sin
from pathlib import Path
from random import Random
import sys

import bpy
import numpy as np

ASSET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ASSET.parents[1] / "conifers/pine/tools"))
from build_pine import write_png
sys.path.insert(0, str(ASSET.parents[1] / "tools"))
from bake_plant_wind import bake

# Name, card width and height (m), blade count, half-width (pixels), seed, RGB.
VARIANTS = (
    ("woodland-grass-carpet", .64, .20, 116, 3.0, 425, (.37, .46, .21)),
    ("woodland-grass-fescue", .51, .29, 91, 2.25, 628, (.35, .43, .27)),
    ("woodland-grass-bank", .72, .38, 89, 4.1, 913, (.36, .48, .22)),
)
WIDTH, HEIGHT = 512, 256


def paint_blades(count, width, seed, green):
    """Rasterize curved blades with graded color and RGB bleed around cutouts."""
    rng = Random(seed)
    y, x = np.mgrid[:HEIGHT, :WIDTH]
    z = HEIGHT - 1 - y
    rgba = np.zeros((HEIGHT, WIDTH, 4), dtype=np.float32)
    rgba[..., :3] = np.array(green) * .70
    blades = [(rng.uniform(.20, .80)*WIDTH, rng.uniform(0, 8),
               rng.triangular(.22, .98, .55)*HEIGHT) for _ in range(count)]
    for root, base, length in sorted(blades, key=lambda blade: blade[2], reverse=True):
        t = np.clip((z-base)/length, 0, 1)
        lean = (root-WIDTH*.5)*rng.uniform(.10,.45) + rng.uniform(-94,94)
        elbow = rng.uniform(-23,23)
        tip = np.clip(root+lean, 7, WIDTH-8)
        center = root+(tip-root)*t**1.45 + elbow*np.sin(pi*t)
        half = width*rng.uniform(.62,1.49) * (1-t)**.65 * (.78+.40*np.sin(pi*t))
        across = x-center
        opacity = np.clip(half-abs(across)+.5, 0, 1)
        opacity *= np.clip(z-base+1,0,1) * np.clip(base+length-z,0,1)
        tint = (.47,.45,.25) if rng.random() < .14 else green
        tint = np.array(tint) * rng.uniform(.78,1.20)
        ridge = np.clip(across/np.maximum(half,1),-1,1)
        fiber = .97+.025*np.sin(1.8*across+.045*z)
        light = (.53+.47*t**.44) * (1+.15*ridge) * fiber
        color = tint * light[..., None]
        # Fill nearby transparent pixels with blade color to reduce mip fringes.
        fringe = (abs(across) < half+3) & (z >= base-2) & (z <= base+length+2)
        clear = fringe & (rgba[..., 3] == 0)
        rgba[..., :3][clear] = color[clear]
        opaque = opacity > 0
        rgba[..., :3][opaque] = color[opaque]
        rgba[..., 3] = np.maximum(rgba[..., 3], opacity)
    return rgba


def make_material(name, texture):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.use_backface_culling = False
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    shader = nodes.get("Principled BSDF")
    shader.inputs["Roughness"].default_value = .88
    image = nodes.new("ShaderNodeTexImage")
    image.image = bpy.data.images.load(str(texture))
    image.image.pack()
    image.image.filepath = "//textures/" + texture.name
    image.extension = "EXTEND"
    cutoff = nodes.new("ShaderNodeMath")
    cutoff.operation = "GREATER_THAN"
    cutoff.inputs[1].default_value = .40
    links.new(image.outputs["Color"], shader.inputs["Base Color"])
    links.new(image.outputs["Alpha"], cutoff.inputs[0])
    links.new(cutoff.outputs[0], shader.inputs["Alpha"])
    return material


def make_clump(name, width, height, material):
    vertices, faces = [], []
    for angle in (0, pi/3, 2*pi/3):
        dx, dy = cos(angle)*width*.5, sin(angle)*width*.5
        first = len(vertices)
        vertices.extend(((-dx,-dy,0), (dx,dy,0), (dx,dy,height), (-dx,-dy,height)))
        faces.append(tuple(range(first, first+4)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(material)
    uv = mesh.uv_layers.new(name="UVMap")
    for face in mesh.polygons:
        for loop, uv_point in zip(face.loop_indices, ((0,0),(1,0),(1,1),(0,1))):
            uv.data[loop].uv = uv_point
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    textures = ASSET / "textures"
    textures.mkdir(exist_ok=True)
    objects = []
    for name, width, height, count, blade_width, seed, green in VARIANTS:
        texture = textures / f"{name}_basecolor.png"
        write_png(texture, paint_blades(count, blade_width, seed, green))
        obj = make_clump(name, width, height, make_material(name, texture))
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        output = ASSET / f"{name}.glb"
        bpy.ops.export_scene.gltf(filepath=str(output), use_selection=True,
                                  export_format="GLB", export_tangents=True)
        bake(output, "grasses", whole_mesh=True)
        objects.append(obj)
    for column, obj in enumerate(objects):
        obj.location.x = (column - 1)*.95
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(ASSET / "woodland-grass-cards.blend"))


if __name__ == "__main__":
    build()

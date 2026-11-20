"""Build the pine, texture maps and studio renders with Blender 4.3."""
from math import cos, sin, tau
from pathlib import Path
from random import Random
import struct
import zlib

import bpy
from mathutils import Vector
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "assets/pine"
MAPS = ASSET / "textures"
RENDERS = ROOT / "renders"
SIZE = 512
rng = Random(48)


def write_png(path, pixels):
    pixels = np.rint(np.clip(pixels, 0, 1) * 255).astype(np.uint8)

    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data)))

    data = b"".join(b"\0" + row.tobytes() for row in pixels)
    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                     + chunk(b"IDAT", zlib.compress(data, 7)) + chunk(b"IEND", b""))


def material(kind):
    y, x = np.mgrid[:SIZE, :SIZE] / SIZE * tau
    noise = np.random.default_rng(71).normal(0, 1, (SIZE, SIZE))
    if kind == "bark":
        warp = x + .026*np.sin(3*y + 2*x) + .012*np.sin(11*y - 3*x)
        plates = (0.5 + 0.5*np.cos(21*warp + .9*np.sin(7*x)))**.52
        splits = (0.5 + 0.5*np.cos(47*warp + np.sin(8*y)))**10
        height = .47 + .28*plates - .18*splits + .06*np.cos(3*y+11*x) + .013*noise
        dark, light = (.20, .105, .062), (.56, .36, .22)
        rough, relief = .95, 1.65
    else:
        patches = .53 + .14*np.cos(9*x+4*y) + .10*np.cos(4*x-7*y)
        sweep = 65*x + 39*y + 2.4*np.sin(8*x-7*y)
        needles = (.5 + .5*np.cos(sweep))**3 * (.5 + .5*np.cos(12*x-21*y))
        height = patches + .14*needles + .033*noise
        dark, light = (.068, .18, .119), (.33, .48, .233)
        rough, relief = .85, .82

    blend = np.clip((height - .18) / .66, 0, 1)[..., None]
    color = np.array(dark) + blend * (np.array(light) - dark)
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) / 2
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) / 2
    normal = np.stack((-dx * relief, dy * relief, np.ones_like(dx)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    roughness = np.clip(rough - .13*(height-.5), 0, 1)
    orm = np.stack((np.clip(.88 + .12*height, 0, 1), roughness,
                    np.zeros_like(height)), axis=-1)
    grayscale = np.repeat(height[..., None], 3, axis=-1)
    paths = {}
    for name, pixels in [("basecolor", color), ("normal", normal*.5 + .5),
                         ("orm", orm), ("height", grayscale)]:
        path = MAPS / f"{kind}_{name}.png"
        write_png(path, pixels)
        paths[name] = path

    mat = bpy.data.materials.new("Pine " + kind.title())
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get("Principled BSDF")
    shader.inputs["Metallic"].default_value = 0
    textures = {}
    for row, name in enumerate(("basecolor", "normal", "orm")):
        node = nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(str(paths[name]))
        if name != "basecolor":
            node.image.colorspace_settings.name = "Non-Color"
        node.image.pack()
        node.image.filepath = "//textures/" + paths[name].name
        node.label = name
        node.location = (-700, -280*row)
        textures[name] = node

    links.new(textures["basecolor"].outputs["Color"], shader.inputs["Base Color"])
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.location = (-280, -240)
    links.new(textures["normal"].outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])
    separate = nodes.new("ShaderNodeSeparateColor")
    separate.location = (-450, -580)
    links.new(textures["orm"].outputs["Color"], separate.inputs[0])
    links.new(separate.outputs["Green"], shader.inputs["Roughness"])
    links.new(separate.outputs["Blue"], shader.inputs["Metallic"])
    group = bpy.data.node_groups.get("glTF Material Output")
    if group is None:
        group = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        group.interface.new_socket(name="Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    output = nodes.new("ShaderNodeGroup")
    output.node_tree = group
    output.location = (-200, -570)
    links.new(separate.outputs["Red"], output.inputs["Occlusion"])
    return mat


def pine_mesh():
    vertices, faces, uvs, materials = [], [], [], []

    def vertex(point):
        vertices.append(point)
        return len(vertices) - 1

    def triangle(ids, coords, material_index):
        faces.append(ids)
        uvs.append(coords)
        materials.append(material_index)

    # One continuous trunk with alternating root flares.
    sides = 10
    trunk = []
    for z, radius, cx, cy in [(0, .32, 0, 0), (.25, .24, 0, 0),
                               (1.4, .19, -.04, .01), (3.5, .12, .055, -.02),
                               (5.3, .07, -.03, .06), (6.73, .022, .08, .04)]:
        trunk.append([
            vertex((cx + cos(i*tau/sides)*radius*(1.24 if z == 0 and i%2 else 1),
                    cy + sin(i*tau/sides)*radius*(1.24 if z == 0 and i%2 else 1), z))
            for i in range(sides)
        ])
    for lower, upper in zip(trunk, trunk[1:]):
        v0, v1 = (vertices[ring[0]][2]*.52 for ring in (lower, upper))
        for i in range(sides):
            j = (i+1) % sides
            u0, u1 = i/sides, (i+1)/sides
            triangle((lower[i], lower[j], upper[j]), ((u0,v0),(u1,v0),(u1,v1)), 0)
            triangle((lower[i], upper[j], upper[i]), ((u0,v0),(u1,v1),(u0,v1)), 0)

    for ring, invert in [(trunk[0], True), (trunk[-1], False)]:
        cap_uv = [(.5 + .45*cos(i*tau/sides), .5 + .45*sin(i*tau/sides))
                  for i in range(sides)]
        for i in range(1, sides-1):
            ids = (0, i+1, i) if invert else (0, i, i+1)
            triangle(tuple(ring[j] for j in ids), tuple(cap_uv[j] for j in ids), 0)

    tiers = [(1.62, 1.96, 1.56, 19), (2.37, 1.75, 1.49, 17),
             (3.15, 1.53, 1.43, 17), (3.91, 1.27, 1.36, 15),
             (4.66, 1.04, 1.26, 13), (5.36, .80, 1.17, 13),
             (5.99, .59, 1.21, 11)]
    for tier, (z, radius, height, count) in enumerate(tiers):
        phase = tier * 1.83
        cx = .12*sin(tier*2.1)
        cy = .10*cos(tier*2.6)
        profile = [
            (phase + i*tau/count + rng.uniform(-.065,.065),
             rng.uniform(.88,1.12) * (.76 if i%3 == 1 else 1),
             rng.uniform(-.19,.14) if i%3 != 1 else rng.uniform(.03,.23))
            for i in range(count)
        ]
        rings = []
        for scale, elevation in [(1, 0), (.68, .37), (.29, .70)]:
            rings.append([
                vertex((cx + cos(a)*radius*r*scale, cy + sin(a)*radius*r*scale,
                        z + height*elevation + irregularity*scale))
                for a, r, irregularity in profile
            ])
        tip = vertex((cx+.13, cy-.055, z+height))
        bottom = vertex((cx, cy, z+.19))
        uv_offset = tier*.27
        for i in range(count):
            j = (i+1) % count
            u0, u1 = 2*i/count + uv_offset, 2*(i+1)/count + uv_offset
            for row, (lower, upper) in enumerate(zip(rings, rings[1:])):
                v0, v1 = (row*.42 + uv_offset, (row+1)*.42 + uv_offset)
                triangle((lower[i], lower[j], upper[j]), ((u0,v0),(u1,v0),(u1,v1)), 1)
                triangle((lower[i], upper[j], upper[i]), ((u0,v0),(u1,v1),(u0,v1)), 1)
            mid = (u0+u1)/2
            triangle((rings[-1][i], rings[-1][j], tip),
                     ((u0,.84+uv_offset),(u1,.84+uv_offset),(mid,1.15+uv_offset)), 1)
            triangle((rings[0][j], rings[0][i], bottom),
                     ((u1,uv_offset),(u0,uv_offset),(mid,uv_offset-.47)), 1)

    mesh = bpy.data.meshes.new("Pine")
    mesh.from_pydata(vertices, [], faces)
    assert not mesh.validate()
    mesh.update()
    for kind in ("bark", "needles"):
        mesh.materials.append(material(kind))
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for polygon, coords, material_index in zip(mesh.polygons, uvs, materials):
        polygon.material_index = material_index
        for index, uv in zip(polygon.loop_indices, coords):
            uv_layer.data[index].uv = uv
    obj = bpy.data.objects.new("Pine", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def studio():
    ground_mat = bpy.data.materials.new("Studio sage")
    ground_mat.diffuse_color = (.21, .27, .245, 1)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.014))
    bpy.context.object.data.materials.append(ground_mat)

    for name, location, power, size, color in [
        ("Key", (1, -6, 10), 1650, 7, (1, .87, .69)),
        ("Fill", (-6, -2, 5), 750, 6, (.68, .82, 1)),
        ("Rim", (2, 5, 8), 2200, 5, (1, .93, .74)),
    ]:
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.size, data.color = power, size, color
        light = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(light)
        light.location = location
        point_at(light, (0, 0, 3.5))

    scene = bpy.context.scene
    world = bpy.data.worlds.new("Studio ambient")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (.38,.45,.51,1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = .32
    scene.world = world
    camera = bpy.data.objects.new("Studio camera", bpy.data.cameras.new("Studio camera"))
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = False
    scene.render.image_settings.file_format = "PNG"
    for name, location, target, scale, resolution in [
        ("pine-full", (11,-17,9.0), (0,0,3.49), 8.65, (840,1050)),
        ("pine-detail", (-8,-10,5.8), (0,0,1.85), 4.6, (1000,800)),
    ]:
        camera.location = location
        point_at(camera, target)
        camera.data.ortho_scale = scale
        scene.render.resolution_x, scene.render.resolution_y = resolution
        scene.render.filepath = str(RENDERS / f"{name}.png")
        bpy.ops.render.render(write_still=True)


def main():
    MAPS.mkdir(parents=True, exist_ok=True)
    RENDERS.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    obj = pine_mesh()
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                view = area.spaces.active
                view.region_3d.view_location = (0, 0, 3.5)
                view.region_3d.view_distance = 11
                view.region_3d.view_rotation = Vector((7,-11,4)).to_track_quat("Z", "Y")
                view.shading.type = "MATERIAL"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(ASSET / "pine.blend"), relative_remap=False)
    bpy.ops.export_scene.gltf(filepath=str(ASSET / "pine.glb"), use_selection=True,
                              export_format="GLB", export_tangents=True)
    print(f"Pine triangles: {len(obj.data.polygons)}", flush=True)
    studio()


if __name__ == "__main__":
    main()

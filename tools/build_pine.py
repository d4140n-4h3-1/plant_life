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
    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6 if pixels.shape[-1] == 4 else 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                     + chunk(b"IDAT", zlib.compress(data, 7)) + chunk(b"IEND", b""))


def needle_spray():
    """Rasterize one shoot with side stems and individual needle silhouettes."""
    random = Random(94)
    rgba = np.zeros((SIZE, SIZE, 4))
    rgba[..., :3] = (.19, .30, .135)
    height = np.full((SIZE, SIZE), .5)

    def stroke(start, end, width, color, ridge):
        margin = int(width + 3)
        x0 = max(0, int(min(start[0], end[0])) - margin)
        x1 = min(SIZE, int(max(start[0], end[0])) + margin)
        y0 = max(0, int(min(start[1], end[1])) - margin)
        y1 = min(SIZE, int(max(start[1], end[1])) + margin)
        y, x = np.mgrid[y0:y1, x0:x1]
        dx, dy = end[0]-start[0], end[1]-start[1]
        t = np.clip(((x-start[0])*dx + (y-start[1])*dy)/(dx*dx + dy*dy), 0, 1)
        distance = np.hypot(x-start[0]-dx*t, y-start[1]-dy*t)
        alpha = np.clip(width*(1-.72*t) + .6 - distance, 0, 1)
        patch = rgba[y0:y1, x0:x1]
        inside = alpha > 0
        shade = .74 + .37*t + .15*np.clip(1-distance/width, 0, 1)
        patch[..., :3][inside] = np.asarray(color) * shade[inside, None]
        patch[..., 3] = np.maximum(patch[..., 3], alpha)
        height[y0:y1, x0:x1][inside] = .5 + ridge*alpha[inside]

    stem = (.32, .24, .11)
    shoots = [((254, 496), (259, 25), 42, 14)]
    for i in range(11):
        y = 454 - i*34
        for side in (-1, 1):
            spread = (126 - 6.5*i) * random.uniform(.81, 1.17)
            shoots.append(((255, y + random.uniform(-11, 11)),
                           (255 + side*spread, y - random.uniform(42, 102)),
                           11, 10))
    for index, (start, end, count, reach) in enumerate(reversed(shoots)):
        dx, dy = end[0]-start[0], end[1]-start[1]
        length = np.hypot(dx, dy)
        along = np.array([dx, dy])/length
        across = np.array([-along[1], along[0]])
        stroke(start, end, 3.4 if count > 20 else 2.2, stem, .24)
        for i in range(count):
            for side in (-1, 1):
                t = (i + random.uniform(.45, 1.1))/(count+1)
                root = np.asarray(start) + t*np.array([dx,dy])
                size = (19 + reach*random.random())*(1-.34*t)*random.uniform(.7, 1.4)
                tip = root + along*size + across*side*size*random.uniform(.55, 1.46)
                value = random.uniform(.7, 1.26)
                base = np.array((.26, .40, .165) if index % 3 else (.30, .43, .17))
                stroke(root, tip, random.uniform(1.45, 2.65), base*value, .23)
    return rgba, height


def pine_bark():
    """Make tileable bark plates with broken edges, flakes and fine grain."""
    v, u = np.mgrid[:SIZE, :SIZE] / SIZE
    x, y = tau*u, tau*v
    columns, rows = 22, 24
    plate_x = columns*u + .28*np.sin(5*y+2*x) + .12*np.sin(19*y-11*x)
    plate_y = rows*v + .46*np.sin(7*x-3*y) + .19*np.sin(17*x+9*y)
    column, row = np.floor(plate_x).astype(int), np.floor(plate_y).astype(int)
    variation = np.random.default_rng(71).random((rows, columns, 3))
    nearest = np.full_like(u, np.inf)
    second = nearest.copy()
    pigment = np.zeros_like(u)
    for offset_y in (-1, 0, 1):
        for offset_x in (-1, 0, 1):
            px, py = column + offset_x, row + offset_y
            jitter_x, jitter_y, plate_tone = variation[py % rows, px % columns].transpose(2, 0, 1)
            distance = ((px + .18 + .64*jitter_x - plate_x)**2
                        + (py + .18 + .64*jitter_y - plate_y)**2)
            closer = distance < nearest
            second = np.where(closer, nearest, np.minimum(second, distance))
            nearest = np.minimum(nearest, distance)
            pigment = np.where(closer, plate_tone, pigment)

    gap = np.sqrt(second) - np.sqrt(nearest)
    fissure = np.exp(-gap/.082)
    bulge = np.clip(gap*1.30, 0, 1)
    flakes = (0.5 + 0.5*np.sin(48*y + 24*x + 2.2*np.sin(13*x-5*y)))**6
    fibers = np.sin(97*x + 2*y + 1.7*np.sin(14*y-3*x))
    weathering = .52 + .23*np.sin(5*x+7*y) + .18*np.sin(11*x-13*y)
    grit = np.random.default_rng(37).normal(0, 1, u.shape)
    height = np.clip(.52 + .16*bulge - .35*fissure + .055*flakes
                     + .032*fibers + .025*grit + .11*pigment, 0, 1)

    rust = np.array((.37, .216, .137))
    ash = np.array((.56, .51, .43))
    mix = np.clip(.56*weathering + .46*pigment + .11*flakes, 0, 1)[..., None]
    color = rust + (ash-rust)*mix
    color *= (.84 + .18*bulge - .67*fissure + .062*fibers + .040*grit)[..., None]
    roughness = np.clip(.93 + .05*fissure - .105*flakes - .06*bulge, 0, 1)
    occlusion = 1 - .42*fissure
    return color, height, roughness, occlusion


def material(kind):
    if kind == "bark":
        color, height, roughness, occlusion = pine_bark()
        relief = 3.4
    else:
        color, height = needle_spray()
        roughness = np.clip(.74 - .13*(height-.5), 0, 1)
        occlusion = np.clip(.88 + .12*height, 0, 1)
        relief = .40

    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) / 2
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) / 2
    normal = np.stack((-dx * relief, dy * relief, np.ones_like(dx)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    orm = np.stack((occlusion, roughness, np.zeros_like(height)), axis=-1)
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
    if kind == "needles":
        clip = nodes.new("ShaderNodeMath")
        clip.operation = "GREATER_THAN"
        clip.inputs[1].default_value = .40
        clip.location = (-270, 40)
        links.new(textures["basecolor"].outputs["Alpha"], clip.inputs[0])
        links.new(clip.outputs[0], shader.inputs["Alpha"])
    else:
        mat.use_backface_culling = True
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

    up = Vector((0, 0, 1))

    def branch(start, end, radius, v_start):
        segment = end-start
        axis = segment.normalized()
        v_end = v_start + .52*segment.length
        side = up.cross(axis).normalized()
        vertical = axis.cross(side)
        rings = [
            [vertex(center + (cos(i*tau/5)*side + sin(i*tau/5)*vertical)*width)
             for i in range(5)]
            for center, width in ((start, radius), (end, radius*.14))
        ]
        root, tip = rings
        for i in range(5):
            j = (i+1)%5
            u0, u1 = i/5, (i+1)/5
            triangle((root[i], root[j], tip[j]), ((u0,v_start),(u1,v_start),(u1,v_end)), 0)
            triangle((root[i], tip[j], tip[i]), ((u0,v_start),(u1,v_end),(u0,v_end)), 0)

    def spray(start, axis, length, breadth):
        direction = axis.normalized()
        side = up.cross(direction).normalized()
        if side.length_squared < .01:
            side = Vector((1, 0, 0))
        vertical = direction.cross(side)
        for angle in (rng.uniform(-.30, .30), rng.uniform(.84, 1.67)):
            offset = (side*cos(angle) + vertical*sin(angle))*breadth*.5
            end = start+direction*length
            corners = [vertex(p) for p in
                       (start-offset*.72, start+offset*.72, end+offset, end-offset)]
            triangle((corners[0], corners[1], corners[2]), ((0,0),(1,0),(1,1)), 1)
            triangle((corners[0], corners[2], corners[3]), ((0,0),(1,1),(0,1)), 1)

    # Irregular whorls leave small gaps through the crown.
    for level in range(13):
        z = 1.39 + level*.409
        spread = 1.99 * (1 - level/14)**.84
        count = 6 if level < 8 else 5
        phase = level*1.79
        for i in range(count):
            angle = phase + i*tau/count + rng.uniform(-.17,.17)
            forward = Vector((cos(angle), sin(angle), 0))
            across = up.cross(forward)
            origin = Vector((0, 0, z + rng.uniform(-.14,.14)))
            reach = spread*rng.uniform(.78, 1.13)
            bend = origin + forward*reach*.49 - up*rng.uniform(.02,.18)
            end = origin + forward*reach + up*rng.uniform(-.12,.28)
            v_start = (level*.317 + i*.593) % 1
            branch(origin, bend, .042 * (1-level/18), v_start)
            branch(bend, end, .024 * (1-level/18), v_start + .52*(bend-origin).length)
            length = .41 + .23*reach
            spray(bend.lerp(end,.70), forward+up*.37, length, length*.67)
            for j, t in enumerate((.42, .56, .69, .82)):
                center = origin.lerp(bend, t*2) if t < .5 else bend.lerp(end, t*2-1)
                for side in (-1, 1):
                    start = center + up*rng.uniform(-.04,.075)
                    heading = forward*rng.uniform(.35,.84) + side*across*rng.uniform(.5,1)
                    heading += up*rng.uniform(-.12,.65)
                    scale = length*rng.uniform(.69,1.25)*(1.03-.07*j)
                    spray(start, heading, scale, scale*rng.uniform(.57,.88))
            spray(origin.lerp(bend,.38), forward+up*.82, length*.84, length*.71)

    for i in range(6):
        angle = i*tau/6
        start = Vector((.06,.04,6.53 + .06*sin(angle)))
        spray(start, Vector((.32*cos(angle),.32*sin(angle),1)), .58, .29)
    spray(Vector((.08,.04,6.64)), up, .56, .26)

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
    scene.cycles.samples = 32
    scene.cycles.transparent_max_bounces = 18
    scene.cycles.use_denoising = False
    scene.render.image_settings.file_format = "PNG"
    for name, location, target, scale, resolution in [
        ("pine-full", (11,-17,9.0), (0,0,3.49), 8.85, (760,950)),
        ("pine-detail", (-8,-10,5.8), (0,0,2.24), 5.15, (900,720)),
        ("pine-bark", (1.8,-5.8,1.65), (0,0,.88), 2.10, (760,900)),
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

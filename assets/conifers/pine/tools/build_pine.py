"""Build the pine, texture maps and studio renders with Blender 4.3."""
import argparse
from math import cos, exp, sin, tau
from pathlib import Path
from random import Random, SystemRandom
import struct
import sys
import zlib

import bpy
from mathutils import Vector
import numpy as np

ASSET = Path(__file__).resolve().parents[1]
SIZE = 512


def write_png(path, pixels):
    pixels = np.rint(np.clip(pixels, 0, 1) * 255).astype(np.uint8)

    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data)))

    data = b"".join(b"\0" + row.tobytes() for row in pixels)
    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6 if pixels.shape[-1] == 4 else 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                     + chunk(b"IDAT", zlib.compress(data, 7)) + chunk(b"IEND", b""))


def needle_spray(spruce=False):
    """Rasterize one shoot with side stems and individual needle silhouettes."""
    random = Random(167 if spruce else 94)
    rgba = np.zeros((SIZE, SIZE, 4))
    rgba[..., :3] = (.14, .24, .135) if spruce else (.19, .30, .135)
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
    shoots = [((254, 496), (259, 25), 70 if spruce else 42, 10 if spruce else 14)]
    for i in range(11):
        y = 454 - i*34
        for side in (-1, 1):
            spread = (126 - 6.5*i) * random.uniform(.81, 1.17)
            shoots.append(((255, y + random.uniform(-11, 11)),
                           (255 + side*spread, y - random.uniform(42, 102)),
                           17 if spruce else 11, 7 if spruce else 10))
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
                size = ((14 if spruce else 19) + reach*random.random())*(1-.34*t)*random.uniform(.7, 1.4)
                tip = root + along*size + across*side*size*random.uniform(.55, 1.46)
                value = random.uniform(.7, 1.26)
                base = np.array((.26, .40, .165) if index % 3 else (.30, .43, .17))
                if spruce:
                    base = np.array((.175, .30, .141) if index % 3 else (.23, .36, .161))
                stroke(root, tip, random.uniform(1.45, 2.65), base*value, .23)
    return rgba, height


def bark_swatch_maps(path):
    """Derive tileable PBR inputs from a bark swatch."""
    image = bpy.data.images.load(str(path))
    image.colorspace_settings.name = "Non-Color"
    assert tuple(image.size) == (SIZE, SIZE)
    pixels = np.empty(SIZE*SIZE*4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    color = pixels.reshape(SIZE, SIZE, 4)[::-1, :, :3].copy()
    bpy.data.images.remove(image)

    # Match opposing edges with smoothly decaying corrections.
    band = 26
    fade = (.5 + .5*np.cos(np.linspace(0, np.pi, band)))[:, None, None]
    for axis in (0, 1):
        rows = np.swapaxes(color, 0, axis)
        difference = .5*(rows[-1]-rows[0])
        rows[:band] += fade*difference
        rows[-band:] -= fade[::-1]*difference

    def blur(values, radius):
        frequencies = np.fft.fftfreq(SIZE)
        kernel = np.exp(-2*np.pi**2*radius**2
                        * (frequencies[:, None]**2 + frequencies[None, :]**2))
        return np.fft.ifft2(np.fft.fft2(values)*kernel).real

    luma = color @ np.array((.2126, .7152, .0722))
    # Reduce broad baked lighting before using the swatch as base color.
    lighting = blur(luma, 38)
    color = np.clip(color - .64*(lighting-np.median(lighting))[..., None], 0, 1)
    height = np.clip(.51 + 2.8*(blur(luma, .75) - blur(luma, 21)), 0, 1)
    recess = np.maximum(.48-height, 0)
    roughness = np.clip(.86 + .16*recess + .16*(blur(luma, 4)-luma), 0, 1)
    occlusion = 1 - .63*recess
    return color, height, roughness, occlusion


def material(kind, maps, *, label="Pine", texture_data=None):
    if texture_data is not None:
        color, height, roughness, occlusion, relief = texture_data
    elif kind == "bark":
        color, height, roughness, occlusion = bark_swatch_maps(ASSET / "source" / "bark_swatch.png")
        relief = 2.7
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
        path = maps / f"{kind}_{name}.png"
        write_png(path, pixels)
        paths[name] = path

    mat = bpy.data.materials.new(label + " " + kind.title())
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


def pine_mesh(maps, seed=None):
    rng = Random(48 if seed is None else seed)
    vertices, faces, uvs, materials = [], [], [], []

    def vertex(point):
        vertices.append(point)
        return len(vertices) - 1

    def triangle(ids, coords, material_index):
        faces.append(ids)
        uvs.append(coords)
        materials.append(material_index)

    # Closely spaced rings let the buttresses taper into the lower trunk.
    profile = [
        # height, radius, center x/y, root flare
        (0, .265, 0, 0, 1),
        (.055, .269, .002, -.003, .90),
        (.135, .261, .008, -.009, .61),
        (.24, .247, .020, -.016, .32),
        (.39, .231, .036, -.019, .12),
        (.57, .221, .050, -.019, .032),
        (.81, .214, .055, -.013, 0),
        (1.12, .199, .044, .004, 0),
        (1.51, .183, .016, .027, 0),
        (2.15, .162, -.039, .040, 0),
        (2.92, .141, -.063, .026, 0),
        (3.73, .118, -.039, -.014, 0),
        (4.57, .094, .008, -.029, 0),
        (5.40, .070, .051, -.006, 0),
        (6.14, .043, .062, .035, 0),
        (6.73, .018, .084, .042, 0),
    ]
    buttresses = [(.24, .22, .24), (1.49, .32, .26), (2.92, .18, .23),
                  (4.27, .38, .25), (5.50, .22, .24)]
    sides = 20
    trunk = []
    for z, radius, cx, cy, flare in profile:
        ring = []
        for i in range(sides):
            angle = i*tau/sides
            ridge = sum(length*exp((cos(angle-direction)-1)/width**2)
                        for direction, length, width in buttresses)
            oval = 1 + .077*cos(2*angle+.29+z*.37) + .038*sin(5*angle+z*.71)
            r = radius*oval + flare*ridge
            ring.append(vertex((cx+cos(angle)*r, cy+sin(angle)*r, z)))
        trunk.append(ring)
    for lower, upper in zip(trunk, trunk[1:]):
        v0, v1 = (vertices[ring[0]][2]*.52 for ring in (lower, upper))
        for i in range(sides):
            j = (i+1) % sides
            u0, u1 = i/sides, (i+1)/sides
            triangle((lower[i], lower[j], upper[j]), ((u0,v0),(u1,v0),(u1,v1)), 0)
            triangle((lower[i], upper[j], upper[i]), ((u0,v0),(u1,v1),(u0,v1)), 0)
    smooth_faces = set(range(len(faces)))

    for ring, record, invert in [(trunk[0], profile[0], True),
                                 (trunk[-1], profile[-1], False)]:
        z, _, cx, cy, _ = record
        center = vertex((cx, cy, z))
        cap_uv = [(.5 + .45*cos(i*tau/sides), .5 + .45*sin(i*tau/sides))
                  for i in range(sides)]
        for i in range(sides):
            j = (i+1) % sides
            first, second = (j, i) if invert else (i, j)
            triangle((center, ring[first], ring[second]),
                     ((.5,.5), cap_uv[first], cap_uv[second]), 0)

    def trunk_center(height):
        for lower, upper in zip(profile, profile[1:]):
            if height <= upper[0]:
                t = (height-lower[0])/(upper[0]-lower[0])
                return Vector((lower[2]*(1-t)+upper[2]*t,
                               lower[3]*(1-t)+upper[3]*t, height))
        return Vector((profile[-1][2], profile[-1][3], height))

    up = Vector((0, 0, 1))

    def woody_shoot(centers, radii, sides, v_start):
        """Sweep shared rings along a branch or taper a twig into a point."""
        first_face = len(faces)
        rings, lengths = [], [v_start]
        for start, end in zip(centers, centers[1:]):
            lengths.append(lengths[-1] + .52*(end-start).length)

        for i, (center, radius) in enumerate(zip(centers, radii)):
            previous = centers[max(0, i-1)]
            following = centers[i+1]
            axis = (following-previous).normalized()
            side = up.cross(axis).normalized()
            vertical = axis.cross(side)
            ring = [
                vertex(center + radius*(cos(k*tau/sides)*side + sin(k*tau/sides)*vertical))
                for k in range(sides)
            ]
            rings.append(ring)

        for row, (lower, upper) in enumerate(zip(rings, rings[1:])):
            v0, v1 = lengths[row:row+2]
            for i in range(sides):
                j = (i+1)%sides
                u0, u1 = i/sides, (i+1)/sides
                triangle((lower[i], lower[j], upper[j]), ((u0,v0),(u1,v0),(u1,v1)), 0)
                triangle((lower[i], upper[j], upper[i]), ((u0,v0),(u1,v1),(u0,v1)), 0)

        tip = vertex(centers[-1])
        for i in range(sides):
            j = (i+1)%sides
            u0, u1 = i/sides, (i+1)/sides
            triangle((rings[-1][i], rings[-1][j], tip),
                     ((u0,lengths[-2]),(u1,lengths[-2]),((u0+u1)*.5,lengths[-1])), 0)
        smooth_faces.update(range(first_face, len(faces)))

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
            attachment = trunk_center(origin.z)
            shoulder = attachment.lerp(bend, .50) + up*.014
            outer = bend.lerp(end, .64) - up*.026
            thickness = .071 * (1-level/17) * (.86 + .19*reach)
            woody_shoot((attachment, shoulder, bend, outer, end),
                        (thickness, .71*thickness, .48*thickness, .20*thickness),
                        5, v_start)
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
                    # Build forks from the limb into the central stems of the sprays.
                    limb = (shoulder.lerp(bend, (t-.25)*4) if t < .5
                            else bend.lerp(outer, (t-.5)/.32))
                    twig_tip = start + heading.normalized() * (.68*scale)
                    twig_radius = thickness * (.25 - .035*j)
                    woody_shoot((limb, twig_tip), (twig_radius,), 3, v_start+t)
            spray(origin.lerp(bend,.38), forward+up*.82, length*.84, length*.71)

    for i in range(6):
        angle = i*tau/6
        start = Vector((.06,.04,6.53 + .06*sin(angle)))
        spray(start, Vector((.32*cos(angle),.32*sin(angle),1)), .58, .29)
    spray(Vector((.08,.04,6.64)), up, .56, .26)

    if seed is not None:
        # Transform wood and foliage together with a ground-level origin.
        shape = Random(f"pine-shape:{seed}")
        height = shape.uniform(5.2, 9.4)
        width = shape.uniform(.77, 1.26)
        crown = shape.uniform(-.24, .33)
        asymmetry = shape.uniform(-.15, .15)
        lean_x, lean_y = (shape.uniform(-.43, .43) for _ in range(2))
        for i, (x, y, z) in enumerate(vertices):
            fraction = z/7.2
            spread = width*(1+crown*sin(tau*.5*fraction))
            bend = fraction**1.6
            vertices[i] = ((1+asymmetry)*x*spread + lean_x*bend,
                           (1-asymmetry)*y*spread + lean_y*bend,
                           height*fraction)

    mesh = bpy.data.meshes.new("Pine")
    mesh.from_pydata(vertices, [], faces)
    assert not mesh.validate()
    mesh.update()
    for kind in ("bark", "needles"):
        mesh.materials.append(material(kind, maps))
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for polygon, coords, material_index in zip(mesh.polygons, uvs, materials):
        polygon.material_index = material_index
        polygon.use_smooth = polygon.index in smooth_faces
        for index, uv in zip(polygon.loop_indices, coords):
            uv_layer.data[index].uv = uv
    obj = bpy.data.objects.new("Pine", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    if seed is not None:
        obj["pine_seed"] = str(seed)
    return obj


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def studio_camera(framing=1, ground_size=200):
    ground_mat = bpy.data.materials.new("Studio sage")
    ground_mat.diffuse_color = (.21, .27, .245, 1)
    bpy.ops.mesh.primitive_plane_add(size=ground_size, location=(0, 0, -.014))
    bpy.context.object.data.materials.append(ground_mat)

    for name, location, power, size, color in [
        ("Key", (1, -6, 10), 1650, 7, (1, .87, .69)),
        ("Fill", (-6, -2, 5), 750, 6, (.68, .82, 1)),
        ("Rim", (2, 5, 8), 2200, 5, (1, .93, .74)),
    ]:
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.size, data.color = power*framing**2, size*framing, color
        light = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(light)
        light.location = Vector(location)*framing
        point_at(light, (0, 0, 3.5*framing))

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
    return scene, camera


PINE_SHOTS = [
    ("pine-full", (11,-17,9.0), (0,0,3.49), 8.85, (760,950)),
    ("pine-detail", (-8,-10,5.3), (0,0,2.03), 4.54, (900,720)),
    ("pine-bark", (1.8,-5.8,1.65), (0,0,.88), 2.10, (760,900)),
]

def studio(render_dir, framing=1, shots=PINE_SHOTS, samples=32):
    scene, camera = studio_camera(framing)
    scene.cycles.samples = samples
    for name, location, target, scale, resolution in shots:
        camera.location = Vector(location)*framing
        point_at(camera, Vector(target)*framing)
        camera.data.ortho_scale = scale*framing
        scene.render.resolution_x, scene.render.resolution_y = resolution
        scene.render.filepath = str(render_dir / f"{name}.png")
        bpy.ops.render.render(write_still=True)


def main(asset=ASSET, mesh_builder=pine_mesh, label="Pine", shots=PINE_SHOTS,
         reference_size=(5, 5, 7.2), studio_scale=1, samples=32):
    parser = argparse.ArgumentParser(description=f"Build a {label} asset with Blender.")
    variation = parser.add_mutually_exclusive_group()
    variation.add_argument("--seed", type=int, help="Generate a reproducible variant.")
    variation.add_argument("--random", action="store_true", help="Choose a new variant seed.")
    parser.add_argument("--output-dir", type=Path, help="Directory for the model and maps.")
    parser.add_argument("--no-renders", action="store_true", help="Skip studio previews.")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    seed = SystemRandom().getrandbits(64) if args.random else args.seed
    if seed is not None:
        print(f"{label} seed: {seed}", flush=True)
    if args.output_dir is not None:
        asset_dir = args.output_dir.resolve()
    elif seed is not None:
        asset_dir = asset / "variants" / f"{asset.name}-{seed}"
    else:
        asset_dir = asset
    render_dir = asset_dir / "renders"
    maps = asset_dir / "textures"
    maps.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    obj = mesh_builder(maps, seed)
    bpy.context.view_layer.update()
    width, depth, height = obj.dimensions
    framing = studio_scale
    if seed is not None:
        framing *= max(value/reference for value, reference in zip(obj.dimensions, reference_size))
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                view = area.spaces.active
                view.region_3d.view_location = (0, 0, height*.49)
                view.region_3d.view_distance = 11*framing
                view.region_3d.view_rotation = Vector((7,-11,4)).to_track_quat("Z", "Y")
                view.shading.type = "MATERIAL"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(asset_dir / f"{asset.name}.blend"), relative_remap=False)
    bpy.ops.export_scene.gltf(filepath=str(asset_dir / f"{asset.name}.glb"), use_selection=True,
                              export_format="GLB", export_tangents=True,
                              export_extras=seed is not None)
    print(f"{label} triangles: {len(obj.data.polygons)}", flush=True)
    print(f"{label} dimensions: {width:.2f} × {depth:.2f} × {height:.2f} m", flush=True)
    if not args.no_renders:
        render_dir.mkdir(parents=True, exist_ok=True)
        studio(render_dir, framing, shots, samples)


if __name__ == "__main__":
    main()

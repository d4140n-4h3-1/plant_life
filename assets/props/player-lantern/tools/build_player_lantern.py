"""Build a low-poly handheld oil lantern and a blocky carry test."""
import argparse
from math import cos, radians, sin, tau
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector

ASSET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ASSET.parent / "hanging-lantern" / "tools"))
from build_lantern import bar, cube, join, mesh, pbr, point_at, revolve


def empty(name, parent=None, position=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.location = position
    obj.empty_display_size = .035
    return obj


def make_lantern():
    grip = empty("HandGrip")
    hinge = empty("LanternHinge", grip, (0, 0, -.115))
    copper = pbr("Oxidized copper", (.27, .11, .047), .64, .49)
    iron = pbr("Dark steel", (.059, .068, .059), .77, .41)
    brass = pbr("Worn brass", (.49, .28, .089), .58, .41)
    glass = pbr("Smoked glass", (.55, .61, .51), 0, .26, alpha=.12)
    ember = pbr("Flame amber", (1, .26, .027), emission=2.8)
    core = pbr("Flame core", (1, .71, .24), emission=4.5)

    bail = [(-.104, 0, -.115), (-.112, 0, -.063), (-.09, 0, -.016),
            (-.056, 0, 0), (.056, 0, 0), (.09, 0, -.016),
            (.112, 0, -.063), (.104, 0, -.115)]
    handle = [bar("Bail segment", a, b, .010, .010, iron, 0)
              for a, b in zip(bail, bail[1:])]
    handle.append(cube("Grip sleeve", (0, 0, 0), (.105, .030, .028), brass, .003))
    join("Carry handle", handle).parent = grip

    frame = [
        revolve("Copper tank", [(.088, -.284), (.105, -.273), (.109, -.251),
                                 (.106, -.226), (.087, -.211)], 8, copper),
        revolve("Dark foot", [(.090, -.288), (.108, -.282), (.109, -.273)], 8, iron),
        revolve("Brass sill", [(.086, -.217), (.107, -.220), (.110, -.213),
                               (.105, -.204)], 8, brass),
        revolve("Shallow copper roof", [(.114, -.076), (.120, -.067), (.109, -.060),
                                       (.067, -.027), (.040, -.025)], 8, copper),
        revolve("Vent crown", [(.038, -.031), (.051, -.027), (.050, -.010),
                               (.040, .001)], 8, iron),
        revolve("Burner collar", [(.030, -.207), (.036, -.193), (.018, -.182)], 8, brass),
    ]
    for side in (-1, 1):
        frame.append(cube("Hinge lug", (.101 * side, 0, 0), (.025, .019, .024), brass))
        frame.append(bar("Hinge strap", (.101 * side, 0, 0),
                         (.10 * side, 0, -.073), .015, .018, iron, 0))
    panes = []
    for i in range(8):
        a, b = (i + .5) * tau / 8, (i + 1.5) * tau / 8
        low = [Vector((.098 * cos(t), .098 * sin(t), -.211)) for t in (a, b)]
        high = [Vector((.103 * cos(t), .103 * sin(t), -.071)) for t in (a, b)]
        frame.append(bar("Cage upright", low[0], high[0], .010, .013, iron, 0))
        corners = [low[0].lerp(low[1], .04), low[1].lerp(low[0], .04),
                   high[1].lerp(high[0], .04), high[0].lerp(high[1], .04)]
        panes.append(mesh("Glass panel", corners, [(0, 1, 2, 3)], glass))
    frame.append(cube("Fill cap", (.038, -.081, -.207), (.027, .023, .018), brass, .002))
    solid = join("Copper lantern and cage", frame)
    solid.parent = hinge
    join("Glass panels", panes).parent = hinge
    flame = revolve("Amber flame", [(.006, -.181), (.010, -.171), (.008, -.156),
                                    (.002, -.138)], 6, ember, at=(.003, 0, 0))
    flame.parent = hinge
    inner = revolve("Flame core", [(.003, -.183), (.005, -.173), (.002, -.154)],
                    6, core)
    inner.parent = hinge
    for obj in (solid, flame, inner):
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(obj.data)
        bm.free()
    data = bpy.data.lights.new("Carry Flame", "POINT")
    data.energy = 8
    data.color = (1, .51, .25)
    data.shadow_soft_size = .013
    light = bpy.data.objects.new("Carry Flame", data)
    bpy.context.collection.objects.link(light)
    light.parent = hinge
    light.location = (0, 0, -.131)

    for frame in range(0, 49, 4):
        phase = tau * (frame % 48) / 48
        hinge.rotation_euler = (radians(13) * sin(phase), 0, 0)
        hinge.keyframe_insert(data_path="rotation_euler", frame=frame)
    hinge.animation_data.action.name = "Carry Sway"
    return grip


def loft(name, rings, material, sides=10):
    """Join tailored elliptical cross sections into a flat-shaded solid."""
    vertices = []
    for center, right, forward, width, depth in rings:
        vertices.extend(center + right * (width * cos(tau * i / sides))
                        + forward * (depth * sin(tau * i / sides)) for i in range(sides))
    faces = [tuple(reversed(range(sides)))]
    for ring in range(len(rings) - 1):
        for i in range(sides):
            a = ring * sides + i
            b = ring * sides + (i + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces.append(tuple(range(len(vertices) - sides, len(vertices))))
    return mesh(name, vertices, faces, material)


def standing(name, profile, material, sides=10):
    return loft(name, [(Vector((x, y, z)), Vector((1, 0, 0)),
                        Vector((0, 1, 0)), width, depth)
                       for z, x, y, width, depth in profile], material, sides)


def limb(name, joints, material, sides=8):
    across = Vector((1, 0, 0))
    points = [Vector(center) for center, _, _ in joints]
    rings = []
    for i, (_, width, depth) in enumerate(joints):
        axis = (points[max(i - 1, 0)] - points[min(i + 1, len(points) - 1)]).normalized()
        front = axis.cross(across).normalized()
        rings.append((points[i], front.cross(axis).normalized(), -front, width, depth))
    return loft(name, rings, material, sides)


def make_player(grip):
    coat = pbr("Olive canvas", (.19, .23, .107), roughness=.9)
    trim = pbr("Dark canvas seams", (.077, .107, .049), roughness=.88)
    leather = pbr("Brown leather", (.103, .055, .028), roughness=.74)
    skin = pbr("Warm skin", (.54, .31, .198), roughness=.76)
    shade = pbr("Lips and ears", (.36, .14, .104), roughness=.81)
    cloth = pbr("Slate trousers", (.087, .108, .121), roughness=.92)
    hair = pbr("Dark brown hair", (.058, .026, .014), roughness=.84)
    eyes = pbr("Eye whites", (.54, .47, .37), roughness=.65)
    iris = pbr("Hazel pupils", (.057, .044, .025), roughness=.69)
    brass = pbr("Dull brass buttons", (.31, .199, .068), .44)
    proxy = empty("PS1 player proxy")
    arm = empty("Carry arm", proxy, (.196, 0, 1.407))

    parts = [
        standing("Tailored jacket", [
            (.947, 0, .008, .166, .108), (1.06, 0, .007, .155, .101),
            (1.17, 0, .013, .144, .099), (1.32, 0, .005, .187, .114),
            (1.409, 0, .007, .206, .093), (1.465, 0, .009, .118, .072),
            (1.482, 0, .005, .057, .056)], coat, 12),
        standing("Belt", [(1.041, 0, .008, .158, .105),
                          (1.082, 0, .008, .158, .105)], leather, 12),
        cube("Belt buckle", (.015, -.103, 1.061), (.047, .016, .032), brass, .004),
        bar("Jacket placket", (0, -.102, 1.09), (0, -.107, 1.37), .019, .013, trim, 0),
        standing("Neck", [(1.443, 0, .009, .054, .054), (1.555, 0, .012, .045, .052)], skin),
        standing("Head and jaw", [
            (1.524, 0, -.013, .036, .064), (1.55, 0, -.004, .065, .076),
            (1.596, 0, .001, .081, .083), (1.631, 0, .010, .081, .080),
            (1.665, 0, .009, .078, .079), (1.709, 0, .015, .070, .067),
            (1.736, 0, .019, .037, .042)], skin, 12),
        standing("Cropped hair", [
            (1.663, 0, .038, .081, .062), (1.699, 0, .017, .080, .083),
            (1.733, -.006, .02, .069, .074),
            (1.753, -.013, .016, .039, .047)], hair, 12),
        mesh("Faceted nose", [(-.014,-.076,1.629), (.014,-.076,1.629),
                             (-.018,-.079,1.586), (.018,-.079,1.586),
                             (0,-.106,1.593), (0,-.088,1.622)],
             [(0,2,4,5), (1,5,4,3), (2,3,4), (0,5,1)], skin),
        bar("Mouth", (-.021,-.080,1.567), (.021,-.080,1.566), .006, .005, shade, 0),
        limb("Relaxed sleeve", [((-.179,.004,1.417),.044,.045), ((-.210,.010,1.365),.063,.066),
                               ((-.238,.024,1.19),.049,.054),
                               ((-.232,-.015,1.084),.047,.048),
                               ((-.239,-.064,.973),.034,.034)], coat),
        limb("Relaxed hand", [((-.239,-.064,.984),.030,.028),
                             ((-.242,-.080,.935),.031,.026),
                             ((-.242,-.092,.898),.021,.020)], skin, 6),
    ]
    for side in (-1, 1):
        parts.extend([
            standing("Ear", [(1.586,.079*side,.012,.008,.013),
                             (1.603,.083*side,.016,.013,.019),
                             (1.630,.081*side,.017,.010,.014)], shade, 6),
            bar("Eye", (.018*side,-.080,1.623), (.055*side,-.060,1.624),
                .012, .012, eyes, .001),
            cube("Pupil", (.035*side,-.077,1.623), (.011,.009,.012), iris),
            bar("Brow", (.017*side,-.080,1.640), (.059*side,-.059,1.645),
                .011, .012, hair, .001),
            bar("Lapel", (.055*side,-.052,1.467), (.012*side,-.110,1.319),
                .028, .015, trim, 0),
        ])
    for z in (1.147, 1.209, 1.269):
        parts.append(cube("Jacket button", (.014, -.111, z), (.011,.007,.011), brass, .001))
    for side, shift in ((-1, .074), (1, -.074)):
        x = .105 * side
        parts.extend([
            limb("Tapered trouser leg", [((x*.8,.005,1.016),.080,.088),
                                        ((x,.008,.771),.073,.078),
                                        ((x*1.12,-.015+shift*.6,.542),.053,.063),
                                        ((x*1.15,shift,.198),.041,.044)], cloth),
            standing("Boot", [(.013,x*1.15,shift-.049,.063,.123),
                              (.048,x*1.15,shift-.049,.063,.123),
                              (.088,x*1.15,shift-.045,.060,.114),
                              (.145,x*1.15,shift,.054,.063),
                              (.238,x*1.15,shift+.005,.048,.051)], leather, 8),
        ])
    join("Traveler body and face", parts).parent = proxy

    socket = (.081, -.291, -.357)
    sleeve = limb("Bent carry sleeve", [((-.019,0,.012),.042,.045),
                                       ((.015,.002,-.034),.061,.063),
                                       ((.048,.007,-.126),.054,.055),
                                       ((.077,-.016,-.234),.052,.052),
                                       ((.088,-.086,-.282),.046,.047),
                                       ((.082,-.237,-.339),.035,.035)], coat)
    cuff = limb("Cuff", [((.082,-.211,-.328),.036,.036),
                         ((.081,-.248,-.344),.035,.032)], trim)
    x, y, z = socket
    palm = cube("Palm", (x, y+.015, z+.012), (.064,.053,.045), skin, .009)
    fingers = [bar("Curled finger", (x+dx,y-.012,z+.025), (x+dx,y-.017,z-.011),
                   .014,.018,skin,.002) for dx in (-.024,-.008,.008,.024)]
    thumb = bar("Thumb", (x+.025,y+.018,z+.018), (x+.035,y-.019,z+.008),
                .018,.018,skin,.003)
    join("Carry sleeve and gripping hand", [sleeve,cuff,palm,*fingers,thumb]).parent = arm
    hand = empty("Preview hand socket", arm, socket)
    grip.parent = hand
    for frame in range(0, 49, 4):
        phase = tau * (frame % 48) / 48
        arm.rotation_euler.x = radians(6) * sin(phase - .45)
        arm.keyframe_insert(data_path="rotation_euler", frame=frame)
        proxy.location.z = .008 * cos(2 * phase)
        proxy.keyframe_insert(data_path="location", frame=frame)


def make_preview(scene, grip):
    make_player(grip)
    plaster = pbr("Plaster", (.16, .19, .205), roughness=.91)
    cube("Test wall", (0, .29, 1.55), (6, .055, 3.1), plaster)
    cube("Test floor", (0, 0, -.045), (6, 6, .063), plaster)
    world = bpy.data.worlds.new("Dusk world")
    world.use_nodes = True
    world.node_tree.nodes.get("Background").inputs["Color"].default_value = (.15, .23, .36, 1)
    world.node_tree.nodes.get("Background").inputs["Strength"].default_value = .23
    scene.world = world
    data = bpy.data.lights.new("Cool test fill", "AREA")
    data.energy, data.size, data.color = 44, 2.1, (.61, .75, 1)
    fill = bpy.data.objects.new("Cool test fill", data)
    bpy.context.collection.objects.link(fill)
    fill.location = (-1.1, -1.55, 2.4)
    point_at(fill, (0, 0, 1.1))

    data = bpy.data.cameras.new("Carry test camera")
    data.lens = 46
    cam = bpy.data.objects.new("Carry test camera", data)
    bpy.context.collection.objects.link(cam)
    cam.location = (.96, -2.44, 1.42)
    point_at(cam, (.075, -.03, .90))
    scene.camera = cam
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 40
    scene.cycles.use_denoising = False
    scene.render.resolution_x, scene.render.resolution_y = 540, 620
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_perspective = "CAMERA"
    return cam


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ASSET)
    parser.add_argument("--no-renders", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.render.fps = 24
    scene.frame_start, scene.frame_end = 0, 48
    grip = make_lantern()
    bpy.ops.export_scene.gltf(filepath=str(output / "player-lantern.glb"),
                              export_format="GLB", export_lights=True,
                              export_animation_mode="ACTIONS")
    cam = make_preview(scene, grip)
    scene.frame_set(9)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "player-lantern.blend"))
    if not args.no_renders:
        renders = output / "renders"
        renders.mkdir(exist_ok=True)
        scene.render.filepath = str(renders / "carry-test.png")
        bpy.ops.render.render(write_still=True)
        cam.location = (.64, -1.03, 1.09)
        point_at(cam, (.26, -.22, .87))
        scene.render.filepath = str(renders / "grip-detail.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()

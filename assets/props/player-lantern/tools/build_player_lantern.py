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


def make_preview(scene, grip):
    coat = pbr("Olive travel coat", (.121, .148, .079), roughness=.88)
    wrap = pbr("Dark leather", (.080, .047, .027), roughness=.77)
    skin = pbr("Warm skin", (.44, .237, .138), roughness=.84)
    cloth = pbr("Charcoal trousers", (.072, .081, .083), roughness=.88)
    buckle = pbr("Buckle", (.28, .205, .103), .47)
    proxy = empty("PS1 player proxy")
    arm = empty("Carry arm", proxy, (.233, -.005, 1.38))
    # The proxy is deliberately built with flat silhouettes and rigid segments.
    parts = [
        cube("Coat", (0, 0, 1.207), (.362, .229, .434), coat, .039),
        cube("Belt", (0, 0, 1.01), (.363, .222, .061), wrap, .012),
        cube("Buckle", (.005, -.122, 1.01), (.068, .018, .044), buckle),
        cube("Scarf", (0, 0, 1.433), (.196, .183, .104), wrap, .022),
        cube("Head", (0, -.012, 1.573), (.184, .178, .236), skin, .026),
        cube("Hood", (0, .039, 1.637), (.211, .188, .177), coat, .033),
        cube("Brow", (0, -.103, 1.596), (.135, .01, .021), wrap),
        bar("Free sleeve", (-.175, 0, 1.371), (-.248, -.03, 1.047),
            .109, .107, coat, .013),
        cube("Free glove", (-.252, -.035, .994), (.083, .073, .113), wrap, .013),
    ]
    for side in (-1, 1):
        parts.extend([
            bar("Trouser leg", (.096 * side, 0, .99), (.119 * side, .019 * side, .315),
                .154, .164, cloth, .018),
            cube("Boot", (.119 * side, -.043 + .019 * side, .178),
                 (.157, .252, .338), wrap, .018),
        ])
    for part in parts:
        part.parent = proxy
    elbow = (.036, -.044, -.269)
    socket = (.038, -.272, -.331)
    for piece in (
        bar("Upper carry sleeve", (0, 0, 0), elbow, .106, .109, coat, .012),
        bar("Lower carry sleeve", elbow, socket, .092, .091, coat, .012),
        cube("Carry glove", socket, (.080, .067, .064), wrap, .012),
    ):
        piece.parent = arm
    hand = empty("Preview hand socket", arm, socket)
    grip.parent = hand
    for frame in range(0, 49, 4):
        phase = tau * (frame % 48) / 48
        arm.rotation_euler.x = radians(9) * sin(phase - .45)
        arm.keyframe_insert(data_path="rotation_euler", frame=frame)
        proxy.location.z = .017 * cos(2 * phase)
        proxy.keyframe_insert(data_path="location", frame=frame)

    plaster = pbr("Plaster", (.16, .19, .205), roughness=.91)
    cube("Test wall", (0, .29, 1.55), (6, .055, 3.1), plaster)
    cube("Test floor", (0, 0, -.045), (6, 6, .063), plaster)
    world = bpy.data.worlds.new("Dusk world")
    world.use_nodes = True
    world.node_tree.nodes.get("Background").inputs["Color"].default_value = (.15, .23, .36, 1)
    world.node_tree.nodes.get("Background").inputs["Strength"].default_value = .23
    scene.world = world
    data = bpy.data.lights.new("Cool test fill", "AREA")
    data.energy, data.size, data.color = 29, 2.1, (.61, .75, 1)
    fill = bpy.data.objects.new("Cool test fill", data)
    bpy.context.collection.objects.link(fill)
    fill.location = (-1.1, -1.55, 2.4)
    point_at(fill, (0, 0, 1.1))

    data = bpy.data.cameras.new("Carry test camera")
    data.lens = 46
    cam = bpy.data.objects.new("Carry test camera", data)
    bpy.context.collection.objects.link(cam)
    cam.location = (1.31, -2.5, 1.47)
    point_at(cam, (.075, -.03, .99))
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
        cam.location = (.64, -.95, 1.04)
        point_at(cam, (.26, -.22, .86))
        scene.render.filepath = str(renders / "grip-detail.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()

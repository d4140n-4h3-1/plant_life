"""Assemble the repository plants into a small woodland clearing."""
import argparse
from math import radians, sin, tau
from pathlib import Path
from random import Random
import sys

import bpy
import numpy as np
from mathutils import Vector

ENVIRONMENT = Path(__file__).resolve().parents[1]
ROOT = ENVIRONMENT.parents[1]
sys.path.insert(0,str(ROOT/"assets"/"conifers"/"pine"/"tools"))
from build_pine import SIZE, material, point_at

ASSETS = {
    "Pine": "conifers/pine/pine.glb",
    "Norway spruce": "conifers/norway-spruce/norway-spruce.glb",
    "Bilberry": "shrubs/bilberry/bilberry.glb",
    "Sheep fescue": "grasses/sheep-fescue/sheep-fescue.glb",
}
X0,X1,Y0,Y1 = -13,13,-14,20
TREES = [
    ("Pine",-5.5,-3.1,1.01), ("Norway spruce",4.6,-1.4,.83),
    ("Pine",-4.3,2.9,.97), ("Norway spruce",5.4,4.4,1.03),
    ("Norway spruce",-5.1,6.4,.90), ("Pine",3.8,8.0,1.04),
    ("Pine",-8.1,3.5,.93), ("Norway spruce",8.2,1.3,.91),
    ("Norway spruce",-8.3,10.4,1.05), ("Pine",-3.0,12.3,.94),
    ("Norway spruce",2.6,12.8,.84), ("Pine",8.9,10.8,1.02),
    ("Pine",-9.7,15.5,.90), ("Norway spruce",6.9,15.8,1.01),
    ("Norway spruce",-1.8,17.5,.78), ("Pine",10.5,16.8,1.02),
]


def trail_x(y):
    return 1.25*np.sin(.29*y)+.33*np.sin(.54*y+.6)


def trail_edge(y):
    return .72+.13*np.sin(.36*y+.3)


def ground_height(x,y):
    hills = (.22*np.sin(.36*x+.24*y)+.20*np.sin(.53*y-.29*x)
             +.087*np.cos(.85*x-.63*y)+.11*np.sin(.28*y+.56*x))
    floor = .052*np.sin(.39*y)+.018*np.sin(.92*y)
    shoulders = np.clip((abs(x-trail_x(y))-.40)/2,0,1)
    return floor+(hills-floor)*shoulders


def terrain_maps():
    v,u = np.mgrid[:SIZE,:SIZE]/(SIZE-1)
    x,y = X0+(X1-X0)*u,Y1-(Y1-Y0)*v
    rng = np.random.default_rng(455)

    def noise(resolution):
        grid = rng.random((resolution+1,resolution+1))
        x,y = np.minimum(u*resolution,resolution-1e-5),np.minimum(v*resolution,resolution-1e-5)
        xi,yi = x.astype(int), y.astype(int)
        fx,fy = x-xi,y-yi
        fx,fy = fx**2*(3-2*fx),fy**2*(3-2*fy)
        return ((grid[yi,xi]*(1-fx)+grid[yi,xi+1]*fx)*(1-fy)
                +(grid[yi+1,xi]*(1-fx)+grid[yi+1,xi+1]*fx)*fy)

    broad = noise(18)
    middle = noise(48)
    fine = noise(145)
    grit = rng.random(u.shape)
    distance = abs(x-trail_x(y))
    bank = trail_edge(y)+.31*(middle-.5)+.14*(fine-.5)
    track = np.clip((bank-distance)/.57+.45,0,1)
    damp = np.clip(.56*broad+.29*middle+.15*fine,0,1)
    earth = np.array((.202,.159,.101))+damp[...,None]*np.array((.163,.127,.082))
    moss = np.array((.14,.176,.079))+damp[...,None]*np.array((.15,.19,.068))
    moss_cover = np.clip((broad*.66+middle*.34-.25)*2.3,0,1)[...,None]
    forest = earth+(moss-earth)*moss_cover
    path = np.array((.327,.263,.174)) + (.52*middle+.29*fine+.19*grit)[...,None]*np.array((.15,.135,.092))
    trail = forest+(path-forest)*track[...,None]
    trail *= (.85+.18*fine+.15*grit)[...,None]
    height = .39+.23*middle+.14*fine+.12*grit
    return trail,height,.88+.08*grit,.89+.08*fine,1.25


def make_ground(maps):
    resolution = 110
    vertices = []
    for row in range(resolution+1):
        y = Y0+(Y1-Y0)*row/resolution
        for column in range(resolution+1):
            x = X0+(X1-X0)*column/resolution
            vertices.append((x,y,float(ground_height(x,y))))
    faces = []
    for j in range(resolution):
        for i in range(resolution):
            a = j*(resolution+1)+i
            b,c = a+1,a+resolution+1
            faces.extend(((a,b,c+1),(a,c+1,c)))
    terrain = bpy.data.meshes.new("Forest floor")
    terrain.from_pydata(vertices,[],faces)
    terrain.update()
    terrain.materials.append(material("terrain",maps,label="Woodland",texture_data=terrain_maps()))
    uv = terrain.uv_layers.new(name="UVMap")
    for face in terrain.polygons:
        face.use_smooth = True
        for index in face.loop_indices:
            x,y,_ = terrain.vertices[terrain.loops[index].vertex_index].co
            uv.data[index].uv = ((x-X0)/(X1-X0),(y-Y0)/(Y1-Y0))
    ground = bpy.data.objects.new("Forest floor and footpath",terrain)
    bpy.context.collection.objects.link(ground)


def plants(seed):
    random = Random(seed)
    templates = {}
    for name, relative in ASSETS.items():
        bpy.ops.object.select_all(action="DESELECT")
        bpy.ops.import_scene.gltf(filepath=str(ROOT/"assets"/relative))
        source, = bpy.context.selected_objects
        mesh = source.data
        mesh.name = name
        templates[name] = mesh
        bpy.data.objects.remove(source,do_unlink=True)

    groups = {}
    for name in ASSETS:
        group = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(group)
        groups[name] = group

    def place(species,x,y,size):
        group = groups[species]
        obj = bpy.data.objects.new(f"{species} {len(group.objects)+1:02d}",templates[species])
        group.objects.link(obj)
        obj.location = (x,y,float(ground_height(x,y))-.011)
        obj.rotation_euler.z = random.random()*tau
        breadth = random.uniform(.83,1.15)
        obj.scale = (size*breadth,size*random.uniform(.87,1.12),size)
        obj["species"] = species

    for species,x,y,size in TREES:
        place(species,x,y,size)

    def valid(x,y,margin):
        return (abs(x-trail_x(y))>trail_edge(y)+margin
                and all((x-tx)**2+(y-ty)**2>.45**2 for _,tx,ty,_ in TREES))

    # Clumps of bilberry range from trail-side specimens to patches under the trees.
    shrub_patches = [
        (-2.85,-7.4), (1.95,-6.7),(-2.25,-4.5),(2.6,-3.3),
        (-3.25,-.85),(2.45,1.1),(-2.9,3.8),(3.1,5.8),(-3.9,6.8),
        (2.5,9.5),(-5.7,8.7),(-5.9,1.4),(6.5,6.1),(1.6,12.1),
    ]
    for x,y in shrub_patches:
        for _ in range(random.randint(2,4)):
            a,b = x+random.uniform(-.66,.66),y+random.uniform(-.62,.62)
            if valid(a,b,.40):
                place("Bilberry",a,b,random.uniform(.73,1.36))

    for side in (-1,1):
        for i in range(24):
            y = -10.8+i*.91+random.uniform(-.41,.41)
            x = float(trail_x(y))+side*(float(trail_edge(y))+random.uniform(.18,1.12))
            for _ in range(random.randint(2,5)):
                a,b = x+random.uniform(-.37,.37),y+random.uniform(-.43,.43)
                if valid(a,b,.03):
                    place("Sheep fescue",a,b,random.uniform(.64,1.37))

    for _ in range(105):
        x,y = random.uniform(-9.4,9.4),random.uniform(-8.8,16.7)
        if valid(x,y,.20):
            place("Sheep fescue",x,y,random.uniform(.61,1.31))

    return {name:len(group.objects) for name,group in groups.items()}


def light_and_cameras():
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("Woodland daylight")
    scene.world.use_nodes = True
    nodes = scene.world.node_tree.nodes
    sky = nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = radians(31)
    sky.sun_rotation = radians(123)
    sky.sun_disc = False
    scene.world.node_tree.links.new(sky.outputs["Color"],nodes["Background"].inputs["Color"])
    nodes["Background"].inputs["Strength"].default_value = .29
    sun = bpy.data.lights.new("Afternoon sun","SUN")
    sun.energy,sun.angle,sun.color = 2.3,radians(7),(1,.87,.72)
    lamp = bpy.data.objects.new("Afternoon sun",sun)
    scene.collection.objects.link(lamp)
    lamp.location = (-7,-9,8)
    point_at(lamp, (0,0,0))

    cameras = []
    for name, location, target, lens in [
        ("Trail view", (-.87,-10.4,1.87),(.25,4.4,2.67),24),
        ("Canopy overview", (3.0,-8.0,28), (0,2.4,1.15), 29),
    ]:
        data = bpy.data.cameras.new(name)
        data.lens = lens
        camera = bpy.data.objects.new(name,data)
        scene.collection.objects.link(camera)
        camera.location = location
        point_at(camera, target)
        cameras.append(camera)
    cameras[1].data.type = "ORTHO"
    cameras[1].data.ortho_scale = 22.4
    scene.camera = cameras[0]
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 20
    scene.cycles.use_denoising = False
    scene.cycles.transparent_max_bounces = 20
    scene.cycles.adaptive_threshold = .10
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x,scene.render.resolution_y = (1140,760)
    return scene,cameras


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed",type=int,default=83)
    parser.add_argument("--output-dir",type=Path,default=ENVIRONMENT)
    parser.add_argument("--no-renders",action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    output = args.output_dir.resolve()
    maps = output/"textures"
    maps.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    make_ground(maps)
    counts = plants(args.seed)
    print(f"Woodland plants: {counts}",flush=True)
    bpy.ops.export_scene.gltf(filepath=str(output/"woodland-clearing.glb"),
                              export_format="GLB",export_tangents=True,export_extras=True)
    scene,cameras = light_and_cameras()
    bpy.ops.file.pack_all()
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=="VIEW_3D":
                area.spaces.active.region_3d.view_perspective = "CAMERA"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output/"woodland-clearing.blend"),relative_remap=False)
    if not args.no_renders:
        renders = output/"renders"
        renders.mkdir(parents=True,exist_ok=True)
        for camera,path,size in zip(cameras,("woodland-trail.png","woodland-overview.png"),((1140,760),(1000,650))):
            scene.camera = camera
            scene.render.resolution_x,scene.render.resolution_y = size
            scene.render.filepath = str(renders/path)
            bpy.ops.render.render(write_still=True)


if __name__=="__main__":
    main()

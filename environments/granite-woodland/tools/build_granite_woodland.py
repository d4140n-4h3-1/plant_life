"""Assemble the collection into a rocky woodland trail."""
import argparse
from collections import Counter
from math import exp, radians, sin, tau
from pathlib import Path
from random import Random
import sys

import bpy
import numpy as np
from mathutils import Vector

ENVIRONMENT=Path(__file__).resolve().parents[1]
ROOT=ENVIRONMENT.parents[1]
sys.path.insert(0,str(ROOT/"assets"/"conifers"/"pine"/"tools"))
from build_pine import point_at

MODELS={
    "Pine":"conifers/pine/pine.glb",
    "Norway spruce":"conifers/norway-spruce/norway-spruce.glb",
    "European larch":"conifers/european-larch/european-larch.glb",
    "English oak":"deciduous/english-oak/english-oak.glb",
    "Silver birch":"deciduous/silver-birch/silver-birch.glb",
    "Common hawthorn":"shrubs/common-hawthorn/common-hawthorn.glb",
    "Common heather":"shrubs/common-heather/common-heather.glb",
    "Hard fern":"ferns/hard-fern/hard-fern.glb",
    "Bracken":"ferns/bracken/bracken.glb",
    "Wood melick":"grasses/wood-melick/wood-melick.glb",
    "Sheep fescue":"grasses/sheep-fescue/sheep-fescue.glb",
    "English bluebell":"wildflowers/english-bluebell/english-bluebell.glb",
    "Oxeye daisy":"wildflowers/oxeye-daisy/oxeye-daisy.glb",
    "Granite boulder":"rocks/granite-rocks/granite-boulder.glb",
    "Granite slab":"rocks/granite-rocks/granite-slab.glb",
    "Granite cobble":"rocks/granite-rocks/granite-cobble.glb",
}
TREES=[
    ("English oak",-5.3,-.5,1.04),("Silver birch",4.7,-1.0,.87),
    ("Pine",-7.3,-4.4,.98),("Norway spruce",7.1,3.4,1.06),
    ("European larch",-5.9,4.2,.89),("Silver birch",.9,5.9,.91),
    ("Norway spruce",-5.7,9.4,.97),("Pine",6.1,8.1,.96),
    ("English oak",5.7,12.0,.93),("European larch",-4.3,15.0,.96),
    ("Silver birch",-1.75,12.7,1.06),("Norway spruce",-9.0,3.4,1.13),
    ("Pine",9.8,13.4,1.1),("Norway spruce",-8.8,15.3,.93),
    ("Pine",-2.9,19.5,1.01),("Norway spruce",5.5,18.7,1.19),
    ("European larch",9.7,18.2,.92),("Silver birch",1.6,19.2,.98),
]
ROCKS=[
    ("Granite boulder",3.7,-5.7,2.00,1.1),("Granite slab",4.8,-6.2,1.67,-.41),
    ("Granite boulder",5.13,-4.35,1.80,.12),("Granite slab",3.54,-3.86,1.82,.61),
    ("Granite slab",6.2,-3.47,1.65,.71),("Granite cobble",2.73,-4.91,1.31,2.75),
    ("Granite boulder",-2.6,-6.1,1.26,-.89),("Granite slab",-2.31,-5.17,1.57,.85),
    ("Granite boulder",-2.7,-2.40,1.06,.55),("Granite slab",-2.01,-.78,1.23,-.66),
    ("Granite boulder",5.1,2.7,1.28,2.31),("Granite slab",4.39,3.33,1.91,.45),
    ("Granite boulder",-3.72,5.53,1.62,-.58),("Granite slab",-2.31,6.31,1.66,-.14),
    ("Granite boulder",-1.88,8.40,1.35,2.63),("Granite slab",1.99,9.42,1.37,-.52),
    ("Granite boulder",1.66,11.4,1.16,1.64),("Granite boulder",-6.1,12.6,1.41,1.18),
]


def trail_x(y):
    return -.17+2.31*sin(.151*(y+9.63))+.37*sin(.49*y-.53)


def edge(y):
    return .78+.15*sin(.33*y+.39)


def height(x,y):
    grade=.031*(y+10)+.16*sin(.46*y+.68)
    dist=abs(x-trail_x(y))
    bank=min(1,max(0,(dist-.54)/1.7))
    bank=bank*bank*(3-2*bank)
    rise=.25*sin(.39*x+.23*y)+.18*sin(.61*y-.27*x)
    rise+=1.19*exp(-((x-5.89)/3.24)**2-((y+4.83)/6.65)**2)
    rise+=.68*exp(-((x+5.66)/3.44)**2-((y-6.93)/8.11)**2)
    return grade+bank*(rise+.12*sin(x*1.61+y*.86)*sin(x*.49-y*1.25))


def load_mesh(relative):
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.import_scene.gltf(filepath=str(ROOT/"assets"/relative))
    source,=bpy.context.selected_objects
    mesh=source.data
    bpy.data.objects.remove(source,do_unlink=True)
    return mesh


def ground(group):
    source=load_mesh("terrain/forest-loam/forest-loam.glb")
    material=source.materials[0]
    nodes,links=material.node_tree.nodes,material.node_tree.links
    bsdf=next(n for n in nodes if n.type=="BSDF_PRINCIPLED")
    base=bsdf.inputs["Base Color"].links[0].from_socket
    tint=nodes.new("ShaderNodeVertexColor")
    tint.layer_name="Trail tint"
    multiply=nodes.new("ShaderNodeMixRGB")
    multiply.blend_type="MULTIPLY"
    multiply.inputs[0].default_value=1
    links.new(base,multiply.inputs[1])
    links.new(tint.outputs["Color"],multiply.inputs[2])
    links.new(multiply.outputs[0],bsdf.inputs["Base Color"])
    size=143
    points,colors=[],[]
    for i in range(size+1):
        y=-14+37*i/size
        for j in range(size+1):
            x=-14+28*j/size
            points.append((x,y,height(x,y)))
            distance=abs(x-trail_x(y))
            noise=.5+.5*sin(1.23*x+.79*y)*sin(1.14*y-.88*x)
            blend=min(1,max(0,(edge(y)+.34*(noise-.5)-distance)/.46+.55))
            moss=.5+.5*sin(1.8*x+.67*y)*sin(.69*x-1.23*y)
            forest=np.array((.37+.21*moss,.69+.21*moss,.48+.15*moss))
            path=np.array((1,.92,.77))*(.92+.079*noise)
            colors.append((*((1-blend)*forest+blend*path),1))
    tris=[]
    for i in range(size):
        for j in range(size):
            a=i*(size+1)+j
            b,c=a+1,a+size+1
            tris.extend(((a,b,c+1),(a,c+1,c)))
    mesh=bpy.data.meshes.new("Loam terrain")
    mesh.from_pydata(points,[],tris)
    mesh.update()
    mesh.materials.append(material)
    uv=mesh.uv_layers.new(name="UVMap")
    color=mesh.color_attributes.new(name="Trail tint",type="FLOAT_COLOR",domain="POINT")
    mesh.color_attributes.active_color=color
    for index,value in enumerate(colors):
        color.data[index].color=value
    for face in mesh.polygons:
        face.use_smooth=True
        for index in face.loop_indices:
            x,y,_=points[mesh.loops[index].vertex_index]
            uv.data[index].uv=(x,y)
    obj=bpy.data.objects.new("Forest loam and trail",mesh)
    group.objects.link(obj)
    bpy.data.meshes.remove(source)


def populate(seed):
    rng=Random(seed)
    world=bpy.context.scene.collection
    groups={}
    for name in ("Terrain","Granite","Canopy","Shrubs","Ferns","Grasses","Wildflowers"):
        groups[name]=bpy.data.collections.new(name)
        world.children.link(groups[name])
    ground(groups["Terrain"])
    meshes={k:load_mesh(v) for k,v in MODELS.items()}
    for key,mesh in meshes.items():
        mesh.name=key
    granite=meshes["Granite boulder"].materials[0]
    for name in ("Granite slab","Granite cobble"):
        original=meshes[name].materials[0]
        meshes[name].materials[0]=granite
        bpy.data.materials.remove(original)
    for image in list(bpy.data.images):
        if image.users==0:
            bpy.data.images.remove(image)
    counts=Counter()

    def place(species,category,x,y,scale,angle=None,settle=.008):
        counts[species]+=1
        obj=bpy.data.objects.new(f"{species} {counts[species]:02d}",meshes[species])
        groups[category].objects.link(obj)
        is_rock=category=="Granite"
        obj.location=(x,y,height(x,y)-settle)
        obj.rotation_euler=(rng.uniform(-.15,.15) if is_rock else 0,
                            rng.uniform(-.15,.15) if is_rock else 0,
                            rng.uniform(0,tau) if angle is None else angle)
        breadth=rng.uniform(.81,1.18)
        obj.scale=(scale*breadth,scale*rng.uniform(.80,1.21),scale*rng.uniform(.89,1.09))
        obj["asset"]=species
        obj["wind"] = not is_rock

    for species,x,y,size in TREES:
        place(species,"Canopy",x,y,size,settle=.034)
    for species,x,y,size,turn in ROCKS:
        place(species,"Granite",x,y,size,turn,settle=.087*size)

    def open_ground(x,y,margin):
        if abs(x-trail_x(y))<edge(y)+margin:
            return False
        if any((x-a)**2+(y-b)**2<.53**2 for _,a,b,_ in TREES):
            return False
        return all((x-a)**2+(y-b)**2>(.43*scale)**2
                   for _,a,b,scale,_ in ROCKS)

    for i in range(77):
        y=rng.uniform(-10.6,16.0)
        sign=1 if i%2 else -1
        x=trail_x(y)+sign*(edge(y)+rng.uniform(.20,4.6))
        if open_ground(x,y,.06):
            name="Granite slab" if i%9==0 else "Granite cobble"
            place(name,"Granite",x,y,rng.uniform(.23,.76),settle=.026)

    patches=[
        ("Common hawthorn","Shrubs",[(-4.0,-3.5),(6.3,-2.2),(-3.7,4.03),(4.9,8.25)],2,.72),
        ("Common heather","Shrubs",[(-2.47,-7.96),(1.55,-6.9),(2.33,-1.68),(3.64,4.19),
                                   (-2.01,5.18),(-3.87,1.93),(3.32,8.42)],5,.91),
        ("Hard fern","Ferns",[(.66,-8.31),(-1.87,-7.35),(2.76,-6.06),(4.54,-4.37),
                               (-1.62,-2.04),(4.51,-.37),(-1.87,3.63),(4.32,5.6)],6,.96),
        ("Bracken","Ferns",[(-3.55,-5.91),(5.10,-1.62),(-2.83,3.55),(4.47,7.71),
                            (-3.84,8.75)],5,.89),
        ("English bluebell","Wildflowers",[(-1.76,-8.18),(1.34,-7.63),(-1.42,-5.9),
                                           (3.44,-1.53),(-1.47,2.85),(4.48,5.92)],6,1.04),
        ("Oxeye daisy","Wildflowers",[(1.63,-5.31),(4.50,-2.18),(-1.06,-1.01),
                                     (3.63,2.51),(-1.64,6.75)],5,.84),
    ]
    for species,category,locations,count,size in patches:
        for x,y in locations:
            for _ in range(count):
                a,b=x+rng.uniform(-.56,.56),y+rng.uniform(-.56,.56)
                if open_ground(a,b,.21):
                    place(species,category,a,b,size*rng.uniform(.72,1.27))

    for i in range(240):
        y=rng.uniform(-11.5,18.2)
        sign=1 if i%2 else -1
        x=trail_x(y)+sign*(edge(y)+rng.uniform(.06,5.3))
        if open_ground(x,y,.04):
            name="Wood melick" if i%6==0 else "Sheep fescue"
            place(name,"Grasses",x,y,rng.uniform(.57,1.35))
    return counts


def setup_studio():
    scene=bpy.context.scene
    sky_world=bpy.data.worlds.new("Clear woodland sky")
    sky_world.use_nodes=True
    scene.world=sky_world
    nodes=sky_world.node_tree.nodes
    sky=nodes.new("ShaderNodeTexSky")
    sky.sky_type="NISHITA"
    sky.sun_elevation=radians(32)
    sky.sun_rotation=radians(144)
    sky.sun_disc=False
    sky_world.node_tree.links.new(sky.outputs["Color"],nodes["Background"].inputs["Color"])
    nodes["Background"].inputs["Strength"].default_value=.34

    sun=bpy.data.lights.new("Warm morning sun","SUN")
    sun.energy,sun.angle,sun.color=2.41,radians(5),(1,.88,.72)
    beam=bpy.data.objects.new("Warm morning sun",sun)
    scene.collection.objects.link(beam)
    beam.location=(-9,-5,7.3)
    point_at(beam,(0,0,0))
    cameras=[]
    for name,location,target,lens in (
        ("Trail entrance",(trail_x(-10.91)-.1,-10.91,height(trail_x(-10.91),-10.91)+1.51),
         (1.68,.91,2.41),25),
        ("Canopy layout",(2.4,-5.8,27),(0,3.14,1.33),33),
    ):
        camera_data=bpy.data.cameras.new(name)
        camera_data.lens=lens
        camera=bpy.data.objects.new(name,camera_data)
        scene.collection.objects.link(camera)
        camera.location=location
        point_at(camera,target)
        cameras.append(camera)
    cameras[1].data.type="ORTHO"
    cameras[1].data.ortho_scale=23.2
    scene.camera=cameras[0]
    scene.render.engine="CYCLES"
    scene.cycles.samples=19
    scene.cycles.adaptive_threshold=.10
    scene.cycles.use_denoising=False
    scene.cycles.transparent_max_bounces=20
    scene.render.resolution_x,scene.render.resolution_y=1180,760
    scene.render.image_settings.file_format="PNG"
    return scene,cameras


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed",type=int,default=147)
    parser.add_argument("--output-dir",type=Path,default=ENVIRONMENT)
    parser.add_argument("--no-renders",action="store_true")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    output=args.output_dir.resolve()
    output.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system="METRIC"
    counts=populate(args.seed)
    print(f"Asset counts: {dict(counts)}",flush=True)
    bpy.ops.export_scene.gltf(filepath=str(output/"granite-woodland.glb"),
                             export_format="GLB",export_tangents=True,export_extras=True,
                             export_vertex_color="ACTIVE",export_all_vertex_colors=False)
    scene,cameras=setup_studio()
    bpy.ops.file.pack_all()
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=="VIEW_3D":
                area.spaces.active.region_3d.view_perspective="CAMERA"
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(output/"granite-woodland.blend"),relative_remap=False)
    if not args.no_renders:
        renders=output/"renders"
        renders.mkdir(exist_ok=True)
        for camera,name,size in zip(cameras,("granite-trail.png","granite-overhead.png"),
                                    ((1180,760),(1020,690))):
            scene.camera=camera
            scene.render.resolution_x,scene.render.resolution_y=size
            scene.render.filepath=str(renders/name)
            bpy.ops.render.render(write_still=True)


if __name__=="__main__":
    main()

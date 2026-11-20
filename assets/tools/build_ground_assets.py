"""Build tiling woodland loam and three weathered granite forms in Blender."""
import argparse
from math import asin, atan2, copysign, cos, pi, sin, tau
from pathlib import Path
from random import Random, SystemRandom
import sys
from tempfile import TemporaryDirectory

import bpy
import numpy as np
from mathutils import Vector

ASSETS = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ASSETS/"conifers"/"pine"/"tools"))
from build_pine import bark_swatch_maps, material, point_at, studio_camera

SOIL = ASSETS/"terrain"/"forest-loam"
ROCKS = ASSETS/"rocks"/"granite-rocks"
RESOLUTION = 1024
FORMS = [
    ("granite-cobble", (.43,.34,.26), 2, 1.0),
    ("granite-slab", (1.26,.79,.32), 2, .58),
    ("granite-boulder", (1.08,.88,.98), 3, .79),
]


def loam_maps():
    """Tileable soil with granular aggregates and sparse organic litter."""
    n=RESOLUTION
    y,x=np.mgrid[:n,:n]/(n-1)
    rng=np.random.default_rng(762)

    def noise(cells):
        lattice=rng.random((cells,cells))
        px,py=x*cells,y*cells
        i,j=px.astype(int),py.astype(int)
        fx,fy=px-i,py-j
        fx,fy=fx*fx*(3-2*fx),fy*fy*(3-2*fy)
        row,next_row=j%cells,(j+1)%cells
        col,next_col=i%cells,(i+1)%cells
        return ((lattice[row,col]*(1-fx)+lattice[row,next_col]*fx)*(1-fy)
                +(lattice[next_row,col]*(1-fx)+lattice[next_row,next_col]*fx)*fy)

    coarse,mid,fine,grain=(noise(frequency) for frequency in (14,58,177,469))
    lumps=.50*mid+.31*fine+.19*grain
    grain_shadow=np.clip((lumps-.43)*3.4+.29,0,1)
    coloration=np.clip(.36*coarse+.47*grain_shadow+.17*grain,0,1)
    tint=np.array((.413,.319,.223))-np.array((.170,.123,.081))
    color=np.array((.170,.123,.081))+coloration[...,None]*tint
    height=.34+.34*lumps+.08*coarse
    roughness=.92+.05*grain-.028*grain_shadow
    ao=.86+.14*grain_shadow

    # Draw small leaf flakes and wood fibers with periodic addressing at tile edges.
    for i in range(182):
        x0,y0=rng.integers(0,n-1,size=2)
        angle=rng.uniform(0,tau)
        length=rng.uniform(2,20)
        width=rng.uniform(.62,2.1 if i%3 else 5.8)
        pad=int(length+width+3)
        grids=np.arange(-pad,pad+1)
        yy,xx=np.meshgrid(grids,grids,indexing="ij")
        lengthwise=(xx*cos(angle)+yy*sin(angle))/length
        crosswise=(yy*cos(angle)-xx*sin(angle))/width
        edge=(1-lengthwise**2)*(.85+.12*np.sin(2.3*lengthwise+i))
        mark=(abs(lengthwise)<1)&(abs(crosswise)<edge)
        row=(y0+yy[mark])%(n-1)
        col=(x0+xx[mark])%(n-1)
        shade=.76+.21*(1-abs(crosswise[mark]))+.10*lengthwise[mark]
        leaf=np.array((.398,.270,.154)) if i%3==0 else np.array((.324,.231,.139))
        color[row,col]=leaf*shade[...,None]*rng.uniform(.72,1.25)
        height[row,col]=.60+.15*shade
        roughness[row,col]=.91
    for data in (color,height,roughness,ao):
        data[-1]=data[0]
        data[:,-1]=data[:,0]
    return color,height,roughness,ao,2.95


def granite_maps():
    color,height,roughness,occlusion=bark_swatch_maps(
        ROCKS/"source"/"surface_swatch.png", resolution=RESOLUTION)
    roughness=np.clip(.79+.79*(roughness-.86),0,1)
    for data in (color,height,roughness,occlusion):
        data[-1]=data[0]
        data[:,-1]=data[:,0]
    return color,height,roughness,occlusion,3.68


def create_tile(size, repeat, mat, name):
    bpy.ops.mesh.primitive_plane_add(size=size)
    obj=bpy.context.object
    obj.name=obj.data.name=name
    obj.data.materials.append(mat)
    layer=obj.data.uv_layers.active
    for uv in layer.data:
        uv.uv *= repeat
    return obj


def create_rock(form, mat, rng):
    name,dimensions,subdivisions,profile=form
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions,radius=1)
    obj=bpy.context.object
    obj.name=obj.data.name=name
    obj.data.materials.append(mat)
    rest=[v.co.normalized() for v in obj.data.vertices]
    offsets=[rng.uniform(0,tau) for _ in range(4)]
    scale=rng.uniform(.75,1.26)
    stretch=Vector(tuple(length*scale*rng.uniform(.84,1.14) for length in dimensions))

    for vertex,p in zip(obj.data.vertices,rest):
        x,y,z=p
        angle=atan2(y,x)
        n=.13*sin(angle*3+.9*z+offsets[0])+.088*cos(5*angle-3*z+offsets[1])
        n+=.082*sin(6*x+4*y+7*z+offsets[2])
        pz=copysign(abs(z)**profile,z)
        if pz<-.42:
            pz=-.42+(pz+.42)*.35
        px=copysign(abs(x)**profile,x)*(1+n)+z*.15*sin(offsets[3])
        py=copysign(abs(y)**profile,y)*(1+n*.71)+z*.11*cos(offsets[3])
        vertex.co=(px,py,pz*(1+n*.49)+.12*x+.10*y*sin(offsets[2]))

    low=Vector(tuple(min(v.co[i] for v in obj.data.vertices) for i in range(3)))
    high=Vector(tuple(max(v.co[i] for v in obj.data.vertices) for i in range(3)))
    origin=Vector(((low.x+high.x)*.5,(low.y+high.y)*.5,low.z))
    span=high-low
    for v in obj.data.vertices:
        v.co=Vector(tuple((v.co[k]-origin[k])*stretch[k]/span[k] for k in range(3)))
    obj.data.update()

    layer=obj.data.uv_layers.active
    turn=rng.uniform(0,1)
    for face in obj.data.polygons:
        face.use_smooth=profile != .58
        keys=[obj.data.loops[i].vertex_index for i in face.loop_indices]
        azimuth=[(atan2(rest[i].y,rest[i].x)/tau)%1 for i in keys]
        if max(azimuth)-min(azimuth)>.5:
            azimuth=[a+1 if a<.5 else a for a in azimuth]
        for j,index in enumerate(keys):
            p=rest[index]
            if abs(p.z)>.99999:
                others=[a for k,a in enumerate(azimuth) if k!=j]
                azimuth[j]=sum(others)/len(others)
            v=asin(max(-1,min(p.z,1)))/pi+.5
            layer.data[face.loop_indices[j]].uv=(azimuth[j]*2+turn,v+.13)
    obj["material_family"]="weathered granite"
    return obj


def save_glb(obj,out):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.gltf(filepath=str(out),export_format="GLB",use_selection=True,
                              export_tangents=True,export_extras=True)


def save_blend(out):
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(out),relative_remap=False)


def shoot_preview(path, location, target, scale, framing):
    scene,camera=studio_camera(framing,ground_size=100)
    camera.location=location
    point_at(camera,target)
    camera.data.ortho_scale=scale
    scene.cycles.samples=27
    scene.render.resolution_x,scene.render.resolution_y=1040,750
    path.parent.mkdir(parents=True,exist_ok=True)
    scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)


def build_soil(output,no_renders):
    maps=output/"textures"
    maps.mkdir(parents=True,exist_ok=True)
    mat=material("soil",maps,label="Forest Loam",texture_data=loam_maps(),tileable=True)
    tile=create_tile(1,1,mat,"Forest loam 1 m tile")
    save_glb(tile,output/"forest-loam.glb")
    save_blend(output/"forest-loam.blend")
    if not no_renders:
        bpy.data.objects.remove(tile,do_unlink=True)
        create_tile(5,5,mat,"Repeating loam")
        shoot_preview(output/"renders"/"forest-loam.png",(1.7,-2.44,2.45),(0,0,0),2.15,.43)


def build_rocks(output,seed,no_renders):
    maps=output/"textures"
    maps.mkdir(parents=True,exist_ok=True)
    mat=material("granite",maps,label="Granite Rocks",texture_data=granite_maps(),tileable=True)
    rng=Random(seed)
    rocks=[create_rock(form,mat,rng) for form in FORMS]
    for obj in rocks:
        obj["rock_seed"]=str(seed)
        save_glb(obj,output/(obj.name+".glb"))
    for obj,location,rotation in zip(rocks,[(-.93,-.47,0),(-.71,.52,0),(.61,.36,0)],
                                    [.38,-.21,.43]):
        obj.location=location
        obj.rotation_euler.z=rotation
    save_blend(output/"granite-rocks.blend")
    if not no_renders:
        with TemporaryDirectory(prefix="granite-loam-") as temp:
            loam=material("soil",Path(temp),label="Forest Loam",texture_data=loam_maps(),tileable=True)
            create_tile(10,10,loam,"Forest loam")
            for i,(x,y) in enumerate(((-.74,-.8),(-.31,-.62),(.23,-.39),(1.11,-.61),
                                       (1.40,.13),(-1.29,.19),(.07,1.09),(.95,1.15))):
                obj=bpy.data.objects.new(f"Cobble {i+1}",rocks[0].data)
                bpy.context.collection.objects.link(obj)
                scale=rng.uniform(.22,.63)
                obj.scale=(scale,scale,scale)
                obj.rotation_euler.z=rng.uniform(0,tau)
                obj.location=(x,y,-.002)
            shoot_preview(output/"renders"/"granite-on-loam.png",(2.9,-5.1,2.92),(0,.09,.33),3.85,.58)


def main(kind):
    asset=SOIL if kind=="soil" else ROCKS
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path)
    parser.add_argument("--no-renders",action="store_true")
    if kind=="rocks":
        variation=parser.add_mutually_exclusive_group()
        variation.add_argument("--seed",type=int)
        variation.add_argument("--random",action="store_true")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system="METRIC"
    if kind=="soil":
        output=args.output_dir.resolve() if args.output_dir else asset
        build_soil(output,args.no_renders)
    else:
        seed=SystemRandom().getrandbits(64) if args.random else args.seed
        destination=asset if seed is None else asset/"variants"/f"granite-{seed}"
        output=args.output_dir.resolve() if args.output_dir else destination
        seed=93 if seed is None else seed
        print(f"Granite seed: {seed}",flush=True)
        build_rocks(output,seed,args.no_renders)

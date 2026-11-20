"""Build a low-poly sheep fescue tuft and reproducible variants in Blender."""
from math import cos, sin, tau
from pathlib import Path
from random import Random
import sys

import bpy
import numpy as np
from mathutils import Vector

ASSET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ASSET.parents[1]/"conifers"/"pine"/"tools"))
from build_pine import SIZE, main, material

UP = Vector((0,0,1))
SHOTS = [
    ("fescue-full", (12,-18,10), (0,0,2.8), 13, (860,720)),
    ("fescue-detail", (9,-12,7.9), (.20,-.11,4.35), 7.8, (850,720)),
]


def grass_maps():
    """Make a striped atlas for fresh blades, weathered blades, and seed heads."""
    v,u = np.mgrid[:SIZE, :SIZE]/SIZE
    band = np.floor(u*3).astype(int)
    x = np.mod(u*3,1)
    vein = .5+.5*np.cos(tau*(7*x+.20*np.sin(tau*v)))
    fiber = .5+.5*np.cos(tau*(31*x+1.8*v))
    wax = np.random.default_rng(48).random(v.shape)
    greens = np.array([(.17,.31,.20),(.25,.37,.218),(.49,.43,.25)])
    colors = greens[band].copy()
    base = np.clip((v-.70)*2.1,0,.6)
    tips = np.clip((.23-v)*3.4,0,1)
    dry = np.array((.53,.46,.25))
    browning = (tips * np.select((band==0, band==1),(.29,.69),default=.23))[...,None]
    colors = colors*(1-browning)+dry*browning
    tint = .75+.24*vein+.11*fiber+.08*wax-.22*base
    colors *= tint[...,None]
    height = .48+.19*vein+.06*fiber+.028*wax
    roughness = .72+.11*base+.08*tips+.03*wax
    return colors,height,roughness,.87+.11*vein,1.1


def fescue_mesh(maps, seed=None, grass_material=None):
    rng = Random(209 if seed is None else seed)
    vertices, triangles, uvs = [], [], []

    def vertex(p):
        vertices.append(p)
        return len(vertices)-1

    def face(ids, coords):
        triangles.append(ids)
        uvs.append(coords)

    def ribbon(path, widths, band, twist=0):
        lo,hi = (band+.018)/3,(band+.982)/3
        rings = []
        for i,(position,width) in enumerate(zip(path,widths)):
            tangent = (path[i+1]-path[max(0,i-1)]).normalized()
            side = UP.cross(tangent).normalized()
            face_normal = tangent.cross(side)
            roll = twist*(i/max(1,len(widths)-1))
            side = side*cos(roll)+face_normal*sin(roll)
            rings.append((vertex(position-side*width*.5),vertex(position+side*width*.5)))
        count = len(widths)
        for i,((a,b),(d,c)) in enumerate(zip(rings,rings[1:])):
            v0,v1 = i/count,(i+1)/count
            face((a,b,c),((lo,v0),(hi,v0),(hi,v1)))
            face((a,c,d),((lo,v0),(hi,v1),(lo,v1)))
        a,b = rings[-1]
        face((a,b,vertex(path[-1])),((lo,(count-1)/count),(hi,(count-1)/count),((lo+hi)*.5,1)))

    for i in range(110):
        angle = i*2.39996+rng.uniform(-.42,.42)
        ray = Vector((cos(angle),sin(angle),0))
        cross = UP.cross(ray)
        spread = rng.random()
        base = ray*(.007+.054*spread)+cross*rng.uniform(-.013,.013)
        reach = rng.uniform(.065,.204)*(.70+.47*spread)
        rise = rng.uniform(.10,.30)*(1-.29*spread)
        peak = rng.uniform(1.30,2.69)
        turn = rng.uniform(-.29,.29)
        width = rng.uniform(.0020,.0055)
        curve = []
        for t in (0,.23,.49,.76,1):
            distance = reach*t**1.69
            z = rise*sin(peak*t)
            curve.append(base+distance*(ray*cos(turn*t)+cross*sin(turn*t))+UP*z)
        ribbon(curve,(width*.39,width,width*.86,width*.45),
               1 if rng.random()<.33 else 0,rng.uniform(-1.22,1.22))

    for i in range(6):
        angle = i*2.39996+.65
        ray = Vector((cos(angle),sin(angle),0))
        cross = UP.cross(ray)
        height = rng.uniform(.255,.352)
        base = ray*rng.uniform(.015,.039)
        lean = rng.uniform(.058,.104)
        path = [base+ray*lean*t*t+UP*(height*t) for t in (0,.44,.73,.92,1)]
        ribbon(path,(.0019,.0016,.0014,.00094),2,rng.uniform(-.42,.42))
        for j in range(7):
            fraction = .77+.032*j
            joint = base+ray*lean*fraction*fraction+UP*(height*fraction)
            fork = (ray*.42+cross*(-1 if j%2 else 1)*.47+UP).normalized()
            length = rng.uniform(.010,.021)*(1-.065*j)
            mid = joint+fork*length*.59
            tip = joint+fork*length
            ribbon((joint,mid,tip),(.0016,.0032),2,rng.uniform(-.65,.65))

    if seed is not None:
        shape = Random(f"fescue-shape:{seed}")
        sx,sy,sz = shape.uniform(.79,1.22),shape.uniform(.78,1.19),shape.uniform(.79,1.20)
        lean_x,lean_y = shape.uniform(-.029,.029),shape.uniform(-.029,.029)
        for i,(x,y,z) in enumerate(vertices):
            bend = (z/.35)**2
            vertices[i] = (x*sx+lean_x*bend,y*sy+lean_y*bend,z*sz)

    mesh = bpy.data.meshes.new("Sheep Fescue")
    mesh.from_pydata(vertices,[],triangles)
    assert not mesh.validate()
    mesh.update()
    if grass_material is None:
        grass_material = material("grass",maps,label="Sheep Fescue",texture_data=grass_maps())
        grass_material.use_backface_culling = False
    mesh.materials.append(grass_material)
    layer = mesh.uv_layers.new(name="UVMap")
    for polygon, coords in zip(mesh.polygons,uvs):
        for index,uv in zip(polygon.loop_indices,coords):
            layer.data[index].uv = uv
    obj = bpy.data.objects.new("Sheep Fescue",mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    if seed is not None:
        obj["fescue_seed"] = str(seed)
    return obj


if __name__ == "__main__":
    main(ASSET,fescue_mesh,"Sheep fescue",SHOTS,
         reference_size=(.46,.46,.35),studio_scale=.35/7.2,samples=30)

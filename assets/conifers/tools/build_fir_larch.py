"""Shared branch, atlas, and export code for silver fir and European larch."""
from dataclasses import dataclass
from math import cos, exp, sin, tau
from pathlib import Path
from random import Random
import sys

import bpy
import numpy as np
from mathutils import Vector

CONIFERS = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(CONIFERS/"pine"/"tools"), str(CONIFERS/"norway-spruce"/"tools")]
from build_pine import SIZE, bark_swatch_maps, main, material
from build_spruce import cone_maps

UP = Vector((0,0,1))


@dataclass(frozen=True)
class Species:
    folder: str
    name: str
    height: float
    reach: float
    tiers: int
    crown_base: float
    salt: int


FIR = Species("silver-fir", "Silver Fir", 12.6, 3.06, 16, .125, 194)
LARCH = Species("european-larch", "European Larch", 12.1, 2.99, 14, .217, 301)


def foliage_maps(larch):
    """Rasterize flat fir needles or radial clusters on larch spur shoots."""
    rng = Random(177 if larch else 213)
    rgba = np.zeros((SIZE,SIZE,4))
    rgba[..., :3] = (.22,.33,.13) if larch else (.13,.24,.137)
    height = np.full((SIZE,SIZE),.5)

    def stroke(start,end,width,color):
        border = int(width)+2
        x0,x1 = max(0,int(min(start[0],end[0]))-border),min(SIZE,int(max(start[0],end[0]))+border)
        y0,y1 = max(0,int(min(start[1],end[1]))-border),min(SIZE,int(max(start[1],end[1]))+border)
        y,x = np.mgrid[y0:y1,x0:x1]
        delta = end-start
        t = np.clip(((x-start[0])*delta[0]+(y-start[1])*delta[1])/np.dot(delta,delta),0,1)
        distance = np.hypot(x-start[0]-delta[0]*t,y-start[1]-delta[1]*t)
        alpha = np.clip(width*(1-.72*t)+.59-distance,0,1)
        mark = alpha>0
        patch = rgba[y0:y1,x0:x1]
        tone = (.79+.18*t+.19*np.clip(1-distance/width,0,1))
        patch[..., :3][mark] = tone[mark,None]*color
        patch[..., 3] = np.maximum(patch[..., 3],alpha)
        h = height[y0:y1,x0:x1]
        h[mark] = .5+.23*alpha[mark]

    stem = np.array((.30,.22,.11))
    base = np.array((255.,496.))
    tip = np.array((259.,20.))
    shoots = [(base,tip)]
    for i in range(10):
        y = 456-i*37
        for side in (-1,1):
            reach = (155-9*i)*rng.uniform(.79,1.16)
            root = np.array((255.,y+rng.uniform(-10,10)))
            end = root+np.array((reach*side,-rng.uniform(35,83)))
            shoots.append((root,end))

    for start,end in reversed(shoots):
        delta = end-start
        axis = delta/np.linalg.norm(delta)
        side = np.array((-axis[1],axis[0]))
        stroke(start,end,2.7,stem)
        central = np.linalg.norm(delta)>300
        if larch:
            count = 17 if central else 6
            for i in range(count):
                p = start+delta*(i+.48)/count
                for needle in range(10):
                    angle = needle*tau/10+rng.uniform(-.39,.39)
                    direction = np.array((cos(angle),sin(angle)))
                    length = rng.uniform(13,33)*(1-.26*i/count)
                    color = np.array((.265,.405,.145))*rng.uniform(.76,1.30)
                    stroke(p,p+direction*length+axis*5,rng.uniform(1.35,2.32),color)
        else:
            count = 62 if central else 22
            for i in range(count):
                p = start+delta*(i+.43)/count
                for sign in (-1,1):
                    reach = rng.uniform(12,22)*(1-.40*i/count)
                    end = p+sign*side*reach+axis*rng.uniform(5,12)
                    color = np.array((.18,.322,.169))*rng.uniform(.72,1.36)
                    stroke(p,end,rng.uniform(1.63,2.59),color)

    return rgba,height,np.clip(.77-.15*(height-.5),0,1),.89+.10*height,.54


class BranchMesh:
    def __init__(self):
        self.positions = []
        self.faces = []
        self.uvs = []
        self.kinds = []

    def vertex(self, point):
        self.positions.append(Vector(point))
        return len(self.positions)-1

    def face(self, vertices, uv, kind=0):
        self.faces.append(vertices)
        self.uvs.append(uv)
        self.kinds.append(kind)

    def join(self, lower, upper, v0, v1, kind=0):
        count = len(lower)
        for i in range(count):
            j = (i+1)%count
            a,b = i/count,(i+1)/count
            self.face((lower[i],lower[j],upper[j]),((a,v0),(b,v0),(b,v1)),kind)
            self.face((lower[i],upper[j],upper[i]),((a,v0),(b,v1),(a,v1)),kind)

    def cap(self, ring, center, v0, v1, kind=0, reverse=False):
        tip = self.vertex(center)
        count = len(ring)
        for i in range(count):
            j = (i+1)%count
            a,b = i/count,(i+1)/count
            ends = (ring[j],ring[i],tip) if reverse else (ring[i],ring[j],tip)
            uv = ((b,v0),(a,v0),((a+b)*.5,v1)) if reverse else ((a,v0),(b,v0),((a+b)*.5,v1))
            self.face(ends,uv,kind)

    def shoot(self, path, radii, sides, offset):
        rings, along = [], [offset]
        for i, radius in enumerate(radii):
            center = path[i]
            axis = (path[i+1]-path[max(i-1,0)]).normalized()
            across = UP.cross(axis).normalized()
            normal = axis.cross(across)
            rings.append([self.vertex(center+radius*(across*cos(tau*j/sides)+normal*sin(tau*j/sides)))
                          for j in range(sides)])
            along.append(along[-1]+.51*(path[i+1]-center).length)
        for i,(lower,upper) in enumerate(zip(rings,rings[1:])):
            self.join(lower,upper,along[i],along[i+1])
        self.cap(rings[-1],path[-1],along[-2],along[-1])

    def spray(self, root, heading, length, width, angle):
        axis = heading.normalized()
        side = UP.cross(axis).normalized()
        normal = axis.cross(side)
        for roll in (-.14,angle):
            edge = width*.5*(side*cos(roll)+normal*sin(roll))
            tip = root+axis*length
            a,b,c,d = [self.vertex(v) for v in
                       (root-.70*edge,root+.70*edge,tip+edge,tip-edge)]
            self.face((a,b,c),((0,0),(1,0),(1,1)),1)
            self.face((a,c,d),((0,0),(1,1),(0,1)),1)

    def cone(self, origin, length, ratio):
        rings = []
        for fraction, radius in ((.04,.61),(.25,1),(.66,.91),(.89,.60)):
            center = origin+UP*length*fraction
            width = length*ratio*radius
            rings.append([self.vertex(center+Vector((width*cos(j*tau/7),width*sin(j*tau/7),0)))
                          for j in range(7)])
        for i,(lower,upper) in enumerate(zip(rings,rings[1:])):
            self.join(lower,upper,.26*i,.26*(i+1),2)
        self.cap(rings[-1],origin+UP*length,.78,1,2)
        self.cap(rings[0],origin,0,-.1,2,reverse=True)


def make_tree(species, maps, seed):
    rng = Random(species.salt if seed is None else seed)
    larch = species == LARCH
    tree = BranchMesh()
    height = species.height

    def center(z):
        t = z/height
        sway = .14 if larch else .073
        return Vector((sway*sin(1.3*t*tau),sway*.61*sin(t*tau-.4)*t,z))

    levels = [height*t for t in (0,.007,.017,.031,.052,.082,.134,.206,.30,.42,.55,.68,.81,.91,.971)]
    roots = ((.20,.27),(1.44,.21),(2.62,.23),(3.86,.30),(5.11,.19))
    trunk = []
    for z in levels:
        center_point = center(z)
        radius = (.292 if larch else .323)*(1-z/height)**.82
        ring = []
        for j in range(18):
            angle = j*tau/18
            flare = sum(size*exp((cos(angle-direction)-1)/.052) for direction,size in roots)
            radius_at_angle = radius*(1+.06*cos(3*angle+.41*z))+flare*exp(-5.2*z)
            ring.append(tree.vertex(center_point+Vector((radius_at_angle*cos(angle),radius_at_angle*sin(angle),0))))
        trunk.append(ring)
    tree.cap(trunk[0],center(0),0,-.1,reverse=True)
    for i,(lower,upper) in enumerate(zip(trunk,trunk[1:])):
        tree.join(lower,upper,levels[i]*.55,levels[i+1]*.55)
    tree.cap(trunk[-1],center(height),levels[-1]*.55,height*.55)
    trunk_vertices = len(tree.positions)

    for tier in range(species.tiers):
        factor = tier/species.tiers
        z = height*(species.crown_base+(.925-species.crown_base)*factor)
        count = (5 if tier<8 else 4) if larch else (6 if tier<10 else 5)
        radius = species.reach*(1-factor)**(.91 if larch else .81)
        for j in range(count):
            angle = tier*1.80+j*tau/count+rng.uniform(-.26,.26)
            ray = Vector((cos(angle),sin(angle),0))
            across = UP.cross(ray)
            root = center(z+rng.uniform(-.15,.15))
            reach = radius*rng.uniform(.72,1.22)
            offset = rng.random()
            elbow = root+ray*reach*.44-UP*reach*(.089 if larch else .041)
            outer = root+ray*reach*.77+UP*reach*rng.uniform(-.065,.026)
            tip = root+ray*reach+UP*reach*rng.uniform(.086,.23)
            thickness = (.059 if larch else .067)*(1-.86*factor)
            path = (root,elbow,outer,tip)
            tree.shoot(path,(thickness,.64*thickness,.27*thickness),5,offset)
            terminal = .28+.19*reach
            tree.spray(outer.lerp(tip,.65),ray+UP*.39,terminal,terminal*.66,.92)
            for row,(a,b,t) in enumerate(((root,elbow,.61),(elbow,outer,.20),
                                           (elbow,outer,.73),(outer,tip,.41))):
                joint = a.lerp(b,t)
                scale = (.25+.275*reach)*(1-.115*row)
                for sign in (-1,1):
                    bearing = ray*rng.uniform(.46,.87)+across*sign*rng.uniform(.48,.93)
                    bearing += UP*rng.uniform(-.11,.32) if larch else UP*rng.uniform(-.15,.19)
                    length = scale*rng.uniform(.81,1.24)
                    direction = bearing.normalized()
                    fork = joint+direction*length*.81
                    tree.shoot((joint,fork),(.22*thickness,),3,offset+row*.19)
                    tree.spray(joint,bearing,length,length*rng.uniform(.69,.89),
                               1.22 if larch else .69)
                    if row in (0,2):
                        offshoot = bearing+UP*(.46 if larch else .31)+ray*.35
                        tree.spray(joint.lerp(fork,.36),offshoot,length*.69,length*.62,
                                   1.26 if larch else .71)
            cone_tiers = (3 <= tier <= 11) if larch else (9 <= tier <= 14)
            if cone_tiers and (j+tier)%3 == 0:
                tree.cone(outer.lerp(tip,.27),
                          rng.uniform(.043,.078) if larch else rng.uniform(.128,.205),
                          .31 if larch else .21)

    for j in range(6):
        angle = tau*j/6
        tree.spray(center(height*(.934+.006*j)),Vector((.43*cos(angle),.43*sin(angle),1)),
                   height*.035,height*.014,1.1)

    minimum = min(v.z for v in tree.positions[trunk_vertices:])
    if minimum < .05:
        for v in tree.positions[trunk_vertices:]:
            if v.z < .65:
                v.z = .65-(.65-v.z)*.60/(.65-minimum)

    if seed is not None:
        shape = Random(f"{species.folder}:{seed}")
        sx,sy,sz = shape.uniform(.80,1.14),shape.uniform(.81,1.17),shape.uniform(.77,1.20)
        lean_x,lean_y = shape.uniform(-.43,.43),shape.uniform(-.43,.43)
        for i,(x,y,z) in enumerate(tree.positions):
            bend = (z/height)**1.7
            tree.positions[i] = (x*sx+lean_x*bend,y*sy+lean_y*bend,z*sz)

    mesh = bpy.data.meshes.new(species.name)
    mesh.from_pydata(tree.positions,[],tree.faces)
    assert not mesh.validate()
    mesh.update()
    asset = CONIFERS/species.folder
    bark = bark_swatch_maps(asset/"source"/"bark_swatch.png")
    cones = cone_maps()
    tone = np.array((1.22,1.10,.79) if larch else (.72,.89,.75))
    cone_data = (np.clip(cones[0]*tone,0,1),*cones[1:])
    for kind,data in (("bark",(*bark,3.0)),("needles",foliage_maps(larch)),("cones",cone_data)):
        mesh.materials.append(material(kind,maps,label=species.name,texture_data=data))
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for polygon, uv, kind in zip(mesh.polygons,tree.uvs,tree.kinds):
        polygon.material_index = kind
        polygon.use_smooth = kind != 1
        for index,value in zip(polygon.loop_indices,uv):
            uv_layer.data[index].uv = value
    obj = bpy.data.objects.new(species.name,mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    if seed is not None:
        obj["conifer_seed"] = str(seed)
    return obj


def build(species):
    asset = CONIFERS/species.folder
    shots = [
        (species.folder+"-full",(10,-17,7.7),(0,0,3.45),8.75,(700,890)),
        (species.folder+"-detail",(-8,-11,4.3),(0,0,2.14 if species==LARCH else 1.67),
         4.45,(820,680)),
    ]
    main(asset,lambda maps, seed: make_tree(species,maps,seed),species.name,shots,
         reference_size=(7.6,7.6,species.height),studio_scale=species.height/7.2,samples=22)

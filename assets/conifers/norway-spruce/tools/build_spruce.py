"""Build a Norway spruce and reproducible variants with Blender 4.3."""
from math import cos, exp, sin, tau
from pathlib import Path
from random import Random
import sys

import bpy
import numpy as np
from mathutils import Vector

ASSET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ASSET.parent / "pine" / "tools"))
from build_pine import SIZE, bark_swatch_maps, main, material, needle_spray

HEIGHT = 11.4
UP = Vector((0, 0, 1))
SHOTS = [
    ("spruce-full", (10, -17, 7.7), (0, 0, 3.54), 8.6, (740, 940)),
    ("spruce-detail", (-8, -12, 4.0), (0, 0, 1.63), 4.0, (880, 700)),
]


def cone_maps():
    """Model overlapping cone scales in the tangential texture."""
    v, u = np.mgrid[:SIZE, :SIZE] / SIZE
    row = v*13
    arch = .29*np.cos(tau*(8*u + .5*np.floor(row)))
    boundary = np.exp(-((np.mod(row + arch, 1)-.5)/.066)**2)
    grain = .5 + .5*np.sin(tau*(131*u+38*v + .23*np.sin(19*tau*v)))
    relief = np.clip(.66 - .36*boundary + .10*grain, 0, 1)
    dark, light = np.array((.24, .118, .058)), np.array((.57, .404, .24))
    color = dark + (light-dark)*relief[..., None]
    return color, relief, .86 + .08*boundary, 1-.35*boundary, 2.4


def spruce_mesh(maps, seed=None):
    random = Random(103 if seed is None else seed)
    vertices, triangles, coordinates, kinds, smooth = [], [], [], [], []

    def point(xyz):
        vertices.append(Vector(xyz))
        return len(vertices)-1

    def face(indices, uv, kind=0, shaded=True):
        triangles.append(indices)
        coordinates.append(uv)
        kinds.append(kind)
        smooth.append(shaded)

    def join(lower, upper, v0, v1, kind=0):
        count = len(lower)
        for i in range(count):
            j = (i+1)%count
            a, b = i/count, (i+1)/count
            face((lower[i], lower[j], upper[j]), ((a,v0),(b,v0),(b,v1)), kind)
            face((lower[i], upper[j], upper[i]), ((a,v0),(b,v1),(a,v1)), kind)

    def cap(ring, xyz, v0, v1, kind=0, reverse=False):
        center = point(xyz)
        count = len(ring)
        for i in range(count):
            a, b = i/count, (i+1)/count
            vertices_uv = [(ring[i], (a,v0)), (ring[(i+1)%count], (b,v0))]
            if reverse:
                vertices_uv.reverse()
            (i0, uv0), (i1, uv1) = vertices_uv
            face((i0,i1,center), (uv0,uv1,((a+b)*.5,v1)), kind, shaded=not reverse)

    def axis_center(z):
        t = z/HEIGHT
        return Vector((.085*sin(t*tau), .062*sin(1.4*t*tau), z))

    roots = [(.17,.26), (1.75,.31), (3.21,.18), (4.72,.32), (5.67,.13)]
    trunk = []
    heights = (0,.10,.24,.46,.76,1.16,2.0,3.05,4.3,5.7,7.15,8.65,10.0,11.05)
    for z in heights:
        center = axis_center(z)
        radius = .276*(1-z/HEIGHT)**.83
        radial = []
        for i in range(18):
            angle = i*tau/18
            extra = sum(length*exp((cos(angle-direction)-1)/.056)
                        for direction, length in roots)
            width = radius*(1+.051*cos(3*angle+.49*z)) + extra*exp(-5*z)
            radial.append(point(center+Vector((width*cos(angle),width*sin(angle),0))))
        trunk.append(radial)
    cap(trunk[0], axis_center(0), 0, -.08, reverse=True)
    for i, (lower, upper) in enumerate(zip(trunk,trunk[1:])):
        join(lower,upper,.54*heights[i],.54*heights[i+1])
    cap(trunk[-1],axis_center(HEIGHT),.54*heights[-1],.54*HEIGHT)
    trunk_vertices = len(vertices)

    def shoot(path, radii, sides, offset):
        rings, along = [], [offset]
        for a, b in zip(path,path[1:]):
            along.append(along[-1]+.54*(b-a).length)
        for i, radius in enumerate(radii):
            axis = (path[i+1]-path[max(i-1,0)]).normalized()
            side = UP.cross(axis).normalized()
            over = axis.cross(side)
            rings.append([point(path[i]+radius*(side*cos(j*tau/sides)+over*sin(j*tau/sides)))
                          for j in range(sides)])
        for i, (lower, upper) in enumerate(zip(rings,rings[1:])):
            join(lower,upper,along[i],along[i+1])
        cap(rings[-1],path[-1],along[-2],along[-1])

    def spray(start, direction, length, width):
        axis = direction.normalized()
        side = UP.cross(axis)
        if side.length_squared < .001:
            side = Vector((1,0,0))
        side.normalize()
        cross = axis.cross(side)
        end = start+axis*length
        for angle in (random.uniform(-.25,.25), random.uniform(.99,1.65)):
            flank = (side*cos(angle)+cross*sin(angle))*width*.5
            a,b,c,d = [point(p) for p in
                       (start-flank*.71,start+flank*.71,end+flank,end-flank)]
            face((a,b,c),((0,0),(1,0),(1,1)),1,False)
            face((a,c,d),((0,0),(1,1),(0,1)),1,False)

    def cone(origin, length):
        rings = []
        for fraction, width in ((0,.13),(.22,.21),(.56,.20),(.84,.135)):
            center = origin + Vector((length*.12*fraction, 0, -length*fraction))
            radius = length*width
            rings.append([point(center+Vector((radius*cos(-k*tau/7),
                                               radius*sin(-k*tau/7),0))) for k in range(7)])
        for i, (upper, lower) in enumerate(zip(rings,rings[1:])):
            join(upper,lower,.26*i,.26*(i+1),2)
        cap(rings[-1],origin+Vector((length*.12,0,-length)),.78,1,2)
        cap(rings[0],origin+UP*.018,0,-.10,2,reverse=True)

    for tier in range(16):
        z = 1.53 + tier*.607
        branch_count = 6 if tier < 9 else 5
        crown = 2.52*(1-tier/16)**1.02
        for index in range(branch_count):
            angle = tier*1.74 + tau*index/branch_count + random.uniform(-.21,.21)
            ray = Vector((cos(angle),sin(angle),0))
            lateral = UP.cross(ray)
            start = axis_center(z+random.uniform(-.18,.18))
            reach = crown*random.uniform(.78,1.17)
            mid = start+ray*reach*.48-UP*reach*.13
            outer = start+ray*reach*.81-UP*reach*.19
            tip = start+ray*reach+UP*reach*random.uniform(-.11,.09)
            width = .059*(1-tier/19)*random.uniform(.83,1.21)
            offset = random.random()
            shoot((start,mid,outer,tip),(width,.61*width,.27*width),5,offset)
            end_length = .26+.19*reach
            spray(outer.lerp(tip,.58),ray+UP*.43,end_length,end_length*.68)
            for row, t in enumerate((.28,.48,.66,.84)):
                joint = (start.lerp(mid,t/.48) if t <= .48 else
                         mid.lerp(outer,(t-.48)/.33) if t <= .81 else
                         outer.lerp(tip,(t-.81)/.19))
                for sign in (-1,1):
                    bearing = ray*random.uniform(.32,.66)+sign*lateral*random.uniform(.45,.89)
                    drop = bearing-UP*random.uniform(.53,1.22)
                    length = (.31+.33*reach)*random.uniform(.78,1.19)*(1-row*.075)
                    end = joint + drop.normalized()*(length*.76)
                    shoot((joint,end),(.23*width,),3,offset+t)
                    spray(joint,drop,length,length*random.uniform(.63,.82))
                    if row in (0,2):
                        secondary = drop*.65 + UP*.28 + ray*.46
                        spray(joint.lerp(end,.31),secondary,length*.64,length*.52)
            if 3 <= tier <= 11 and (index+tier)%4 == 0:
                cone(outer.lerp(tip,.28),random.uniform(.108,.187))

    for i in range(7):
        angle = i*tau/7
        ray = Vector((cos(angle),sin(angle),0))
        spray(axis_center(10.72+i*.042),ray*.44+UP,.36,.16)

    # Give the lowest weeping sprays ground clearance even on broad variants.
    lowest = min(position.z for position in vertices[trunk_vertices:])
    if lowest < 0:
        for position in vertices[trunk_vertices:]:
            if position.z < .9:
                position.z = .9 - (.9-position.z)*.82/(.9-lowest)

    if seed is not None:
        original_height = max(position.z for position in vertices)
        shape = Random(f"spruce-shape:{seed}")
        height = shape.uniform(8.3,15.2)
        breadth = shape.uniform(.77,1.24)
        taper = shape.uniform(-.17,.18)
        skew = shape.uniform(-.13,.13)
        lean_x, lean_y = (shape.uniform(-.48,.48) for _ in range(2))
        for i,(x,y,z) in enumerate(vertices):
            fraction = z/original_height
            spread = breadth*(1+taper*sin(tau*.5*fraction))
            bend = fraction**1.7
            vertices[i] = ((1+skew)*x*spread+lean_x*bend,
                           (1-skew)*y*spread+lean_y*bend,height*fraction)

    name = "Norway Spruce"
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], triangles)
    assert not mesh.validate()
    mesh.update()
    bark = bark_swatch_maps(ASSET/"source"/"bark_swatch.png")
    color, height = needle_spray(spruce=True)
    foliage = (color,height,np.clip(.75-.14*(height-.5),0,1),
               np.clip(.88+.12*height,0,1),.46)
    for kind,data in (("bark",(*bark,2.7)),("needles",foliage),("cones",cone_maps())):
        mesh.materials.append(material(kind,maps,label=name,texture_data=data))
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for polygon, uv, kind, shaded in zip(mesh.polygons,coordinates,kinds,smooth):
        polygon.material_index = kind
        polygon.use_smooth = shaded
        for index, value in zip(polygon.loop_indices,uv):
            uv_layer.data[index].uv = value
    obj = bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    if seed is not None:
        obj["spruce_seed"] = str(seed)
    return obj


if __name__ == "__main__":
    main(ASSET, spruce_mesh, "Norway spruce", SHOTS,
         reference_size=(6.3,6.3,HEIGHT), studio_scale=HEIGHT/7.2, samples=26)

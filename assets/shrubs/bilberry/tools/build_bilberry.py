"""Generate a fruiting bilberry shrub and seeded variants in Blender."""
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

UP = Vector((0, 0, 1))
SHOTS = [
    ("bilberry-full", (13,-18,12), (0,0,3.25), 12.9, (900,760)),
    ("bilberry-detail", (8,-14,9), (.75,-1.15,4.18), 5.4, (900,710)),
]


def leaf_maps():
    """A cutout atlas with green and bronze-edged bilberry leaves."""
    v, u = np.mgrid[:SIZE, :SIZE]/(SIZE-1)
    panel = u >= .5
    axis = np.mod(u*2, 1)*2-1
    t = np.clip((v-.035)/.93, 0, 1)
    curve = .82*np.sin(np.pi*t)**.79*(.87+.23*t)
    teeth = .027*np.cos(41*tau*t)*np.sin(np.pi*t)**.32
    edge = curve + teeth - abs(axis+.05*np.sin(tau*t))
    margin = 1-np.clip(3.8*edge, 0, 1)
    midrib = np.exp(-abs(axis+.05*np.sin(tau*t))*34)
    ribs = np.exp(-abs(np.sin(tau*(6.8*t+1.26*abs(axis))))*13)
    ribs *= np.clip(abs(axis)*3, 0, 1)*(1-.63*abs(axis))
    flecks = .52+.17*np.sin(tau*(9*u+17*v))+.12*np.cos(tau*(19*u-16*v))
    grit = np.random.default_rng(173).random(v.shape)-.5
    height = .53 + .14*midrib + .075*ribs + .09*flecks + .027*grit
    green = np.array((.188,.327,.106)) + (flecks+.24*ribs)[...,None]*np.array((.14,.19,.081))
    green += (.75*midrib+.28*ribs)[...,None]*np.array((.15,.15,.054))
    green += (panel*.053 + .035*grit)[...,None]*np.array((1,.76,.35))
    green += (panel*margin**4)[...,None]*np.array((.13,-.055,-.006))
    alpha = np.clip(edge*128+.5, 0, 1)
    alpha *= ((v>.04)&(v<.966))
    rgba = np.concatenate((green,alpha[...,None]),axis=-1)
    roughness = .64+.11*flecks-.055*ribs
    return rgba,height,roughness,.92+.06*height,.78


def stem_maps():
    v,u = np.mgrid[:SIZE, :SIZE]/SIZE
    ridges = .5+.5*np.sin(tau*(9*u+.14*np.sin(3*tau*v)))
    striation = .5+.5*np.sin(tau*(47*u+3*v+.12*np.sin(7*tau*v)))
    stain = .50+.23*np.cos(tau*(u+v))+.14*np.sin(tau*(3*u-5*v))
    height = .46+.22*ridges+.07*striation
    brown, green = np.array((.36,.28,.13)),np.array((.40,.51,.243))
    color = brown + stain[...,None]*(green-brown)
    color *= (.81+.23*ridges+.09*striation)[...,None]
    return color,height,.85-.11*ridges,.89+.10*ridges,1.2


def fruit_maps():
    v,u = np.mgrid[:SIZE, :SIZE]/SIZE
    cloud = .55 + .17*np.sin(tau*(4*u+3*v)) + .15*np.cos(tau*(11*u-7*v))
    speckle = np.random.default_rng(158).random(u.shape)
    # Mesh UVs run from the stem downward to the recessed blossom crown.
    crown = np.clip((.13-v)*12,0,1)
    lobes = (.5+.5*np.cos(5*tau*u))*crown
    dark = np.array((.081,.096,.17))
    blue = np.array((.375,.454,.59))
    bloom = np.clip(.31+.48*cloud+.11*speckle-.48*crown+.20*lobes,0,1)
    color = dark+(blue-dark)*bloom[...,None]
    height = .60-.19*crown+.065*lobes+.02*speckle
    return color,height,.55+.21*bloom,1-.28*crown,1.4


def bilberry_mesh(maps, seed=None):
    rng = Random(318 if seed is None else seed)
    points, triangles, uvs, materials, smoothing = [], [], [], [], []

    def vertex(position):
        points.append(Vector(position))
        return len(points)-1

    def face(tri, uv, kind=0, smooth=True):
        triangles.append(tri)
        uvs.append(uv)
        materials.append(kind)
        smoothing.append(smooth)

    def join(bottom, top, v0, v1, kind=0):
        for i in range(len(bottom)):
            j = (i+1)%len(bottom)
            a,b = i/len(bottom),(i+1)/len(bottom)
            face((bottom[i],bottom[j],top[j]),((a,v0),(b,v0),(b,v1)),kind)
            face((bottom[i],top[j],top[i]),((a,v0),(b,v1),(a,v1)),kind)

    def cap(ring, position, v0, v1, kind=0, reverse=False):
        tip = vertex(position)
        for i in range(len(ring)):
            j = (i+1)%len(ring)
            a,b = i/len(ring),(i+1)/len(ring)
            ends = ((ring[j],(b,v0)),(ring[i],(a,v0))) if reverse else (
                    (ring[i],(a,v0)),(ring[j],(b,v0)))
            face((ends[0][0],ends[1][0],tip),(ends[0][1],ends[1][1],((a+b)*.5,v1)),kind)

    def stem(path, widths, sides=4, grounded=False):
        rings = []
        v = [rng.random()]
        for i, (center, width) in enumerate(zip(path, widths)):
            prev, following = path[max(0,i-1)], path[i+1]
            axis = (following-prev).normalized()
            side = UP.cross(axis).normalized()
            front = axis.cross(side)
            ring = []
            for j in range(sides):
                angle = j*tau/sides
                p = center + width*(cos(angle)*side + sin(angle)*front)
                if grounded and i == 0:
                    p.z = 0
                ring.append(vertex(p))
            rings.append(ring)
            v.append(v[-1]+(following-center).length*5)
        if grounded:
            cap(rings[0],path[0],v[0],v[0]-.1,reverse=True)
        for i,(lower,upper) in enumerate(zip(rings,rings[1:])):
            join(lower,upper,v[i],v[i+1])
        cap(rings[-1],path[-1],v[-2],v[-1])

    def leaf(root, heading, length, young=False):
        axis = heading.normalized()
        lateral = UP.cross(axis).normalized()
        normal = axis.cross(lateral)
        roll = rng.uniform(-.65,.65)
        side = cos(roll)*lateral + sin(roll)*normal
        half = length*rng.uniform(.239,.33)
        levels = [root,root+axis*length*.50+normal*length*.078,root+axis*length]
        rings = [(vertex(center-side*half),vertex(center+side*half)) for center in levels]
        lo,hi = (.506,.994) if young else (.006,.494)
        for i, ((a,b),(d,c)) in enumerate(zip(rings,rings[1:])):
            v0,v1 = i*.5,(i+1)*.5
            face((a,b,c),((lo,v0),(hi,v0),(hi,v1)),1,False)
            face((a,c,d),((lo,v0),(hi,v1),(lo,v1)),1,False)

    def berry(top, radius):
        rings = []
        for fraction, width in ((.20,.74),(.57,1),(.90,.69)):
            center = top-UP*radius*1.74*fraction
            rings.append([vertex(center+Vector((radius*width*cos(-j*tau/7),
                                                radius*width*sin(-j*tau/7),0)))
                          for j in range(7)])
        join(rings[0],rings[1],.17,.52,2)
        join(rings[1],rings[2],.52,.92,2)
        cap(rings[0],top,.17,0,2,reverse=True)
        cap(rings[-1],top-UP*radius*1.63,.92,1,2)

    for i in range(19):
        angle = i*2.39996+rng.uniform(-.25,.25)
        outward = Vector((cos(angle),sin(angle),0))
        cross = UP.cross(outward)
        rank = (i/18)**.65
        height = (.68-.28*rank)*rng.uniform(.88,1.11)
        spread = (.115+.272*rank)*rng.uniform(.82,1.17)
        bottom = outward*(.011+.046*rank)
        bend = bottom+outward*spread*.37+UP*height*.51
        apex = bottom+outward*spread+cross*rng.uniform(-.053,.053)+UP*height
        upper = bend.lerp(apex,.51)
        size = rng.uniform(.0028,.0046)
        stem((bottom,bend,upper,apex),(size,.65*size,.37*size),grounded=True)
        for row, t in enumerate((.30,.42,.54,.65,.77,.89)):
            if t < .5:
                joint = bottom.lerp(bend, 2*t)
            elif t < .75:
                joint = bend.lerp(upper, 4*(t-.5))
            else:
                joint = upper.lerp(apex, 4*(t-.75))
            sign = -1 if (row+i)%2 else 1
            direction = (outward*rng.uniform(.26,.81)+cross*sign*rng.uniform(.62,1.07)
                         +UP*rng.uniform(-.14,.50)).normalized()
            reach = rng.uniform(.083,.148)*(1-.44*t)
            knee = joint+direction*reach*.56+UP*.012
            tip = joint+direction*reach
            stem((joint,knee,tip),(size*.40,size*.24),3)
            twig_side = UP.cross(direction).normalized()
            leaf(joint, outward*.83-cross*sign*.34+UP*.50, rng.uniform(.029,.043))
            for node, frac in enumerate((.08,.22,.38,.52,.65,.79,.92)):
                attachment = joint.lerp(knee,frac/.56) if frac<.56 else knee.lerp(tip,(frac-.56)/.44)
                side = -1 if (node+row)%2 else 1
                heading = direction*rng.uniform(.32,.94)+twig_side*side*.80+UP*rng.uniform(-.17,.58)
                leaf(attachment,heading,rng.uniform(.024,.047)*(1-.23*frac),rng.random()<.17)
                if node in (1,3,5):
                    back = direction*.70-twig_side*side*.58+UP*rng.uniform(.18,.62)
                    leaf(attachment,back,rng.uniform(.022,.035),rng.random()<.12)
            if (i+row*2)%5==0 and row>0:
                fruit_base = joint.lerp(knee,.62)
                fruit_top = fruit_base+twig_side*sign*.007-UP*rng.uniform(.009,.019)
                stem((fruit_base,fruit_top),(.00052,),3)
                berry(fruit_top,rng.uniform(.0038,.0060))
        for j in range(4):
            side = -1 if j%2 else 1
            leaf(upper.lerp(apex,.80+.058*j),outward*.55+cross*side+UP*.26,
                 rng.uniform(.019,.035),True)

    if seed is not None:
        shape = Random(f"bilberry-shape:{seed}")
        sx,sy,sz = shape.uniform(.73,1.23),shape.uniform(.76,1.24),shape.uniform(.76,1.25)
        lean_x,lean_y = shape.uniform(-.08,.08),shape.uniform(-.08,.08)
        for i,(x,y,z) in enumerate(points):
            bend = (z/.68)**2
            points[i] = (x*sx+lean_x*bend,y*sy+lean_y*bend,z*sz)

    mesh = bpy.data.meshes.new("Bilberry")
    mesh.from_pydata(points,[],triangles)
    assert not mesh.validate()
    mesh.update()
    for kind, data in (("stems",stem_maps()),("leaves",leaf_maps()),("berries",fruit_maps())):
        mesh.materials.append(material(kind,maps,label="Bilberry",texture_data=data))
    layer = mesh.uv_layers.new(name="UVMap")
    for polygon, coords, kind, shaded in zip(mesh.polygons,uvs,materials,smoothing):
        polygon.material_index = kind
        polygon.use_smooth = shaded
        for index, uv in zip(polygon.loop_indices,coords):
            layer.data[index].uv = uv
    obj = bpy.data.objects.new("Bilberry",mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    if seed is not None:
        obj["bilberry_seed"] = str(seed)
    return obj


if __name__ == "__main__":
    main(ASSET,bilberry_mesh,"Bilberry",SHOTS,
         reference_size=(1.0,1.0,.67),studio_scale=.67/7.2,samples=28)

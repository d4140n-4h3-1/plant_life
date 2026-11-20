"""Build English bluebell and common poppy flowering clumps and seeded variants."""
from math import cos, sin, tau
from pathlib import Path
from random import Random
import sys

import numpy as np
from mathutils import Vector

ASSETS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ASSETS/"conifers"/"tools"))
from build_fir_larch import BranchMesh, UP
from build_pine import SIZE, main
from build_birch_heather import finish, stem_maps
from build_wildflowers import bell, blade, ground_stem, leaves
from build_rowan_foxtail_daisy import granular_maps, radial_mesh


def bluebell_maps():
    v,u=np.mgrid[:SIZE,:SIZE]/SIZE
    face=np.mod(2*u,1)
    veins=np.exp(-abs(np.sin(tau*(6*face+.12*v)))*8)
    translucency=(1-v)**.72
    tint=.52+.30*translucency+.11*veins
    dark=np.array((.192,.248,.551))
    bright=np.array((.432,.466,.786))
    color=dark+tint[...,None]*(bright-dark)
    color+=(u>=.5)[...,None]*np.array((.071,.050,.092))
    height=.46+.16*veins+.06*translucency
    return color,height,.59+.16*height,.89+.10*height,.75


def poppy_maps():
    v,u=np.mgrid[:SIZE,:SIZE]/SIZE
    fiber=.55+.22*np.sin(tau*(10*u+2.3*v+.29*np.sin(v*4)))+.12*np.cos(tau*(37*u-3*v))
    crease=.5+.5*np.cos(tau*(7*u+.69*v+.22*np.sin(v*7)))
    center=(np.clip((v-.59)*4.2,0,1)**1.3)*np.exp(-((u-.5)*2.25)**4)
    scarlet=np.array((.83,.139,.081))+(fiber*.12+crease*.048)[...,None]*np.array((.62,.38,.30))
    throat=np.array((.136,.060,.064))
    color=scarlet+(throat-scarlet)*center[...,None]
    height=.47+.16*fiber+.089*crease
    return color,height,.61+.16*height,.91+.08*height,.78


def bluebell_mesh(maps,seed=None):
    rng=Random(453 if seed is None else seed)
    tree=BranchMesh()
    for i in range(53):
        angle=i*2.39996+rng.uniform(-.22,.22)
        ray=Vector((cos(angle),sin(angle),0))
        root=ray*rng.uniform(.014,.112)+UP*rng.uniform(.004,.035)
        heading=ray*rng.uniform(.64,1.08)+UP*rng.uniform(.25,1.21)
        length=rng.uniform(.134,.288)
        blade(tree,root,heading,length,length*rng.uniform(.048,.103),rng.uniform(-.71,.71))

    for i in range(11):
        angle=i*2.39996+.46
        ray=Vector((cos(angle),sin(angle),0))
        side=UP.cross(ray)
        base=ray*rng.uniform(.014,.133)+side*rng.uniform(-.017,.017)
        rise=rng.uniform(.279,.436)
        lean=rng.uniform(.074,.145)
        parameters=(0,.23,.43,.63,.79,.90,1)
        path=[base+ray*lean*t**2+UP*rise*(sin(t*1.76)) for t in parameters]
        size=rng.uniform(.0028,.0043)
        ground_stem(tree,path,tuple(size*f for f in (1,.79,.65,.53,.40,.24)))
        for j in range(6):
            t=.54+j*.078
            k=next(a for a in range(len(parameters)-1) if parameters[a+1]>=t)
            p=path[k].lerp(path[k+1],(t-parameters[k])/(parameters[k+1]-parameters[k]))
            sway=rng.uniform(-.73,.57)
            ray2=ray*rng.uniform(.60,.87)+side*sway-UP*rng.uniform(.68,1.25)
            length=rng.uniform(.021,.035)*(1-.046*j)
            origin=p+ray2.normalized()*(.019-.00175*j)+UP*.003
            tree.shoot((p,origin),(.00122,),3,.29)
            bell(tree,origin,ray2,length,length*rng.uniform(.225,.298),bluebell=True)

    for position in tree.positions:
        position.z=max(position.z,0)
    raw=stem_maps()
    stalk=(np.clip(raw[0]*np.array((.75,1.29,.73)),0,1),*raw[1:])
    return finish(tree,maps,"English Bluebell",(("stems",stalk),("leaves",leaves(False)),
                  ("bells",bluebell_maps())),seed,((.75,1.20),(.77,1.21),(.76,1.22)),
                  smooth_kinds=(0,2))


def poppy_flower(tree,origin,heading,radius,rng):
    axis=heading.normalized()
    side=UP.cross(axis).normalized()
    forward=axis.cross(side)
    cup=tree.vertex(origin)
    phase=rng.uniform(0,tau)
    outline=((.23,-.24),(.44,-.48),(.68,-.59),(.91,-.44),(1.0,-.21),
             (.974,0),(1,.23),(.92,.44),(.68,.59),(.44,.48),(.23,.24))
    for i in range(4):
        azimuth=phase+i*tau/4
        ray=side*cos(azimuth)+forward*sin(azimuth)
        left=axis.cross(ray)
        outline_points=[]
        lift=rng.uniform(.24,.49)
        for j,(distal,across) in enumerate(outline):
            coil=distal**1.49*(lift+.058*sin(2.49*j+i))
            outline_points.append(tree.vertex(origin+radius*(ray*distal+left*across+axis*coil)))
        uv=[(.5+side*.73,distal) for distal,side in outline]
        center=tree.vertex(origin+radius*(ray*.55+axis*.112))
        for j in range(len(outline_points)-1):
            tree.face((center,outline_points[j],outline_points[j+1]),((.50,.55),uv[j],uv[j+1]),2)
        tree.face((cup,outline_points[0],center),((.5,0),uv[0],(.5,.55)),2)
        tree.face((cup,center,outline_points[-1]),((.5,0),(.5,.55),uv[-1]),2)
    disc=radius*.21
    rows=((.015*radius,.84*disc),(.082*radius,1.25*disc),(.177*radius,.62*disc))
    radial_mesh(tree,origin,axis,rows,9,3)


def poppy_mesh(maps,seed=None):
    rng=Random(316 if seed is None else seed)
    tree=BranchMesh()
    for i in range(28):
        angle=i*2.39996
        ray=Vector((cos(angle),sin(angle),0))
        root=ray*rng.uniform(.020,.117)+UP*rng.uniform(.007,.048)
        length=rng.uniform(.084,.166)
        blade(tree,root,ray+UP*rng.uniform(.13,.67),length,length*.31,rng.uniform(-.36,.43))
    for i in range(12):
        angle=i*2.39996+.19
        ray=Vector((cos(angle),sin(angle),0))
        side=UP.cross(ray)
        base=ray*rng.uniform(.025,.151)
        rise=rng.uniform(.31,.681)
        spread=rng.uniform(.057,.232)
        path=[base+ray*spread*t**1.66+side*.034*sin(np.pi*t)+UP*rise*t
              for t in (0,.26,.52,.75,1)]
        diameter=rng.uniform(.0024,.0040)
        ground_stem(tree,path,(diameter,diameter*.71,diameter*.53,diameter*.39))
        for j,p in enumerate(path[1:4]):
            side_sign=-1 if (i+j)%2 else 1
            segment=ray*.71+side*side_sign*.42+UP*rng.uniform(.15,.61)
            length=rng.uniform(.072,.111)*(1-.23*j)
            blade(tree,p,segment,length,length*.31,rng.uniform(-.51,.51))
        facing=UP+ray*rng.uniform(.35,.81)+side*rng.uniform(-.39,.39)
        poppy_flower(tree,path[-1],facing,rng.uniform(.028,.048),rng)
    raw=stem_maps()
    stalk=(np.clip(raw[0]*np.array((.76,1.33,.72)),0,1),*raw[1:])
    pollen=granular_maps("disc")
    grain=pollen[1]
    dark=np.array((.041,.036,.055))+grain[...,None]*np.array((.18,.143,.187))
    disc=(dark,*pollen[1:])
    return finish(tree,maps,"Common Poppy",(("stems",stalk),("leaves",leaves(False,lobed=True)),
                  ("petals",poppy_maps()),("pollen",disc)),
                  seed,((.75,1.20),(.77,1.21),(.76,1.22)),smooth_kinds=(0,2,3))


def build(slug):
    if slug=="english-bluebell":
        name,mesh,size,width="English bluebell",bluebell_mesh,.45,.64
        aim=4.20
    else:
        name,mesh,size,width="Common poppy",poppy_mesh,.67,.84
        aim=4.70
    shots=[(slug+"-full",(11,-17,13),(0,0,3.06),11.3,(840,770)),
           (slug+"-detail",(8,-12,11),(.29,-.19,aim),5.55,(850,710))]
    main(ASSETS/"wildflowers"/slug,mesh,name,shots,
         reference_size=(width,width,size),studio_scale=size/7.2,samples=23)

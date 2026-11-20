"""Procedural builders for a rowan tree, meadow foxtail, and oxeye daisy."""
from math import cos, exp, sin, tau
from pathlib import Path
from random import Random
import sys

import numpy as np
from mathutils import Vector

ASSETS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ASSETS/"conifers"/"tools"))
from build_fir_larch import BranchMesh, UP
from build_pine import SIZE, bark_swatch_maps, main
from build_birch_heather import atlas, finish, stem_maps
from build_wildflowers import blade, flower_maps, ground_stem, leaves, petalled_flower


def granular_maps(kind):
    y,x=np.mgrid[:SIZE,:SIZE]/SIZE
    grit=np.random.default_rng(731).random(x.shape)
    cell=.5+.5*np.cos(tau*(32*x+.44*np.sin(tau*25*y)))
    fleck=.5+.5*np.cos(tau*(48*y+15*x))
    grain=.45*cell+.38*fleck+.17*grit
    tones={
        "fruit":((.394,.080,.031),(.86,.298,.096)),
        "ears":((.319,.335,.148),(.554,.482,.246)),
        "disc":((.62,.295,.019),(.99,.77,.058)),
    }
    dark,light=(np.array(rgb) for rgb in tones[kind])
    blend=.31+.61*grain
    color=dark+(light-dark)*blend[...,None]
    height=.42+.24*grain
    return color,height,.61+.25*grain,.90+.09*grain,1.28


def radial_mesh(tree,origin,axis,rows,sides,kind,close_base=True):
    """Join a series of rings, terminating in a filled end face."""
    axis=axis.normalized()
    across=UP.cross(axis)
    if across.length_squared<.001:
        across=Vector((1,0,0))
    across.normalize()
    normal=axis.cross(across)
    rings=[]
    for distal,radius in rows:
        center=origin+axis*distal
        rings.append([tree.vertex(center+radius*(across*cos(j*tau/sides)+normal*sin(j*tau/sides)))
                      for j in range(sides)])
    for i,(a,b) in enumerate(zip(rings,rings[1:])):
        tree.join(a,b,i/len(rows),(i+1)/len(rows),kind)
    top,radius=rows[-1]
    tree.cap(rings[-1],origin+axis*(top+.37*radius),(len(rows)-1)/len(rows),1,kind)
    if close_base:
        bottom,radius=rows[0]
        tree.cap(rings[0],origin+axis*(bottom-.44*radius),0,-.065,kind,reverse=True)


def rowan_mesh(maps,seed=None):
    rng=Random(801 if seed is None else seed)
    tree=BranchMesh()
    h=9.65

    def center(z):
        t=z/h
        return Vector((.22*sin(.9*t*tau)+.14*t,.16*sin(t*tau)*t,z))

    heights=[h*t for t in (0,.014,.041,.082,.149,.235,.354,.49,.64,.78,.91,.965)]
    trunk=[]
    for z in heights:
        width=.228*(1-z/h)**.77
        ring=[]
        for i in range(15):
            angle=i*tau/15
            buttress=.19*exp(-5.3*z)*max(cos(5*angle+.3),0)**3
            r=width*(1+.055*cos(3*angle+z*.62))+buttress
            ring.append(tree.vertex(center(z)+Vector((r*cos(angle),r*sin(angle),0))))
        trunk.append(ring)
    tree.cap(trunk[0],center(0),0,-.07,reverse=True)
    for i,(a,b) in enumerate(zip(trunk,trunk[1:])):
        tree.join(a,b,heights[i]*.59,heights[i+1]*.59)
    tree.cap(trunk[-1],center(h),heights[-1]*.59,h*.59)

    for tier in range(12):
        f=tier/11
        z=h*(.207+.719*f)
        span=.53+2.49*sin(np.pi*(.23+.756*f))**.84
        for j in range(6 if tier<7 else 4):
            angle=tier*1.80+j*tau/(6 if tier<7 else 4)+rng.uniform(-.21,.23)
            ray=Vector((cos(angle),sin(angle),0))
            side=UP.cross(ray)
            start=center(z+rng.uniform(-.19,.19))
            reach=span*rng.uniform(.83,1.18)
            thickness=.071*(1-.87*f)*rng.uniform(.80,1.11)
            elbow=start+ray*reach*.37+UP*reach*.26
            wrist=start+ray*reach*.75+UP*reach*.34
            tip=start+ray*reach+UP*reach*rng.uniform(.16,.31)
            tree.shoot((start,elbow,wrist,tip),(thickness,.56*thickness,.27*thickness),5,rng.random())
            for i,root in enumerate((elbow,elbow.lerp(wrist,.56),wrist,wrist.lerp(tip,.49))):
                for sign in (-1,1):
                    heading=ray*rng.uniform(.43,.86)+side*sign*rng.uniform(.52,.90)+UP*rng.uniform(-.26,.33)
                    length=(.33+.198*reach)*(1-.10*i)*rng.uniform(.83,1.20)
                    fork=root+heading.normalized()*length*.73
                    tree.shoot((root,fork),(.24*thickness,),3,i*.24)
                    tree.spray(root,heading,length,length*.79,1.14)
                    if i in (0,2):
                        tree.spray(root.lerp(fork,.36),heading+UP*.41,length*.68,length*.60,1.08)
            tree.spray(wrist.lerp(tip,.62),ray+UP*.36,.31+.18*reach,.33+.12*reach,1.23)
            if 2<=tier<=10 and (tier+j)%3==0:
                fork=wrist.lerp(tip,.34)
                stem=fork+ray*.22-UP*.115
                tree.shoot((fork,stem),(.010,),3,.10)
                for k in range(7):
                    bearing=k*2.39996
                    p=stem+.051*(ray*cos(bearing)+side*sin(bearing))-UP*rng.uniform(.004,.057)
                    radius=rng.uniform(.010,.017)
                    tree.shoot((stem,p+UP*.014),(.0019,),3,.12)
                    radial_mesh(tree,p,UP,((0,.56*radius),(radius,.95*radius),(radius*1.69,.50*radius)),5,2)
    for i in range(7):
        z=8.93+i*.053
        angle=i*tau/7
        tree.spray(center(z),Vector((cos(angle),sin(angle),.64)),.58,.42,1.12)
    bark=bark_swatch_maps(ASSETS/"deciduous"/"rowan"/"source"/"bark_swatch.png")
    return finish(tree,maps,"Rowan",(("bark",(*bark,2.26)),("leaves",atlas("rowan")),
                                    ("berries",granular_maps("fruit"))),
                  seed,((.79,1.20),(.80,1.19),(.76,1.23)),smooth_kinds=(0,2))


def foxtail_mesh(maps,seed=None):
    rng=Random(267 if seed is None else seed)
    tree=BranchMesh()
    for j in range(104):
        angle=j*2.39996+rng.uniform(-.43,.43)
        ray=Vector((cos(angle),sin(angle),0))
        root=ray*rng.uniform(.015,.118)+UP*rng.uniform(.006,.043)
        heading=ray*rng.uniform(.61,1)+UP*rng.uniform(.66,1.64)
        length=rng.uniform(.135,.358)
        blade(tree,root,heading,length,length*rng.uniform(.029,.061),rng.uniform(-.79,.79))
    for j in range(17):
        angle=j*2.39996+.3
        ray=Vector((cos(angle),sin(angle),0))
        width=rng.uniform(.0021,.0037)
        base=ray*rng.uniform(.009,.091)
        rise=rng.uniform(.43,.75)
        lean=rng.uniform(.14,.281)
        path=[base+ray*lean*t**1.5+UP*rise*t for t in (0,.30,.57,.83,1)]
        ground_stem(tree,path,(width,width*.74,width*.56,width*.42))
        for k,p in enumerate(path[1:-1]):
            angle2=angle+(k+1)*1.67
            heading=Vector((cos(angle2),sin(angle2),.78))
            length=rng.uniform(.110,.193)*(1-.18*k)
            blade(tree,p,heading,length,length*.054,rng.uniform(-.6,.6))
        seed_axis=(path[-1]-path[-2]).normalized()
        length=rng.uniform(.057,.102)
        radius=rng.uniform(.0047,.0078)
        rows=tuple((t*length,d*radius) for t,d in ((0,.49),(.19,.91),(.49,1),(.77,.86),(.95,.45)))
        radial_mesh(tree,path[-1],seed_axis,rows,7,2)
    stalk=stem_maps()
    return finish(tree,maps,"Meadow Foxtail",
                  (("stems",(np.clip(stalk[0]*np.array((.83,1.24,.74)),0,1),*stalk[1:])),
                   ("blades",leaves(False)),("seedheads",granular_maps("ears"))),
                  seed,((.75,1.19),(.76,1.23),(.77,1.22)),smooth_kinds=(0,2))


def daisy_mesh(maps,seed=None):
    rng=Random(615 if seed is None else seed)
    tree=BranchMesh()
    for i in range(34):
        angle=i*2.39996+rng.uniform(-.25,.25)
        ray=Vector((cos(angle),sin(angle),0))
        root=ray*rng.uniform(.008,.118)+UP*rng.uniform(.008,.050)
        length=rng.uniform(.081,.154)
        blade(tree,root,ray+UP*rng.uniform(.10,.60),length,length*.27,rng.uniform(-.57,.57))
    for i in range(14):
        angle=i*2.39996+.29
        ray=Vector((cos(angle),sin(angle),0))
        base=ray*rng.uniform(.021,.140)
        rise=rng.uniform(.223,.523)
        lean=rng.uniform(.041,.153)
        path=[base+ray*lean*t**2+UP*rise*t for t in (0,.26,.54,.79,1)]
        width=rng.uniform(.002,.0036)
        ground_stem(tree,path,(width,.72*width,.57*width,.40*width))
        for j,p in enumerate(path[1:4]):
            heading=Vector((cos(angle+j*2.4),sin(angle+j*2.4),.44))
            length=rng.uniform(.043,.087)*(1-.18*j)
            blade(tree,p,heading,length,length*.24,rng.uniform(-.44,.44))
        facing=UP+ray*rng.uniform(.32,.74)
        radius=rng.uniform(.022,.034)
        petalled_flower(tree,path[-1],facing,radius,rng.uniform(0,tau),petals=17)
        disc=radius*.34
        rows=((-disc*.095,disc*.64),(disc*.08,disc),(disc*.28,disc*.88))
        radial_mesh(tree,path[-1],facing,rows,9,3)
    stalk=stem_maps()
    pale=flower_maps(True)
    petals=(np.clip(pale[0]*np.array((1.025,1.04,1.08)),0,1),*pale[1:])
    return finish(tree,maps,"Oxeye Daisy",
                  (("stems",(np.clip(stalk[0]*np.array((.78,1.29,.71)),0,1),*stalk[1:])),
                   ("leaves",leaves(False)),("petals",petals),("pollen",granular_maps("disc"))),
                  seed,((.78,1.23),(.78,1.24),(.77,1.23)),smooth_kinds=(0,2,3))


def build(slug):
    folder,name,mesh,size,span,detail={
        "rowan":("deciduous","Rowan",rowan_mesh,9.65,7.4,3.5),
        "meadow-foxtail":("grasses","Meadow foxtail",foxtail_mesh,.80,.87,4.2),
        "oxeye-daisy":("wildflowers","Oxeye daisy",daisy_mesh,.52,.69,4.4),
    }[slug]
    scale=9.05 if slug=="rowan" else 10.6
    shots=[(slug+"-full",(12,-17,10),(0,0,3.19),scale,(810,790)),
           (slug+"-detail",(8,-12,9),(.06,0,detail),4.45,(845,700))]
    main(ASSETS/folder/slug,mesh,name,shots,
         reference_size=(span,span,size),studio_scale=size/7.2,samples=23)

"""English oak and common hawthorn geometry and seeded build entry points."""
from math import cos, exp, sin, tau
from pathlib import Path
from random import Random
import sys

import numpy as np
from mathutils import Vector

ASSETS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ASSETS/"conifers"/"tools"))
from build_fir_larch import BranchMesh, UP
from build_pine import bark_swatch_maps, main
from build_birch_heather import atlas, finish, stem_maps
from build_rowan_foxtail_daisy import granular_maps, radial_mesh


def oak_mesh(maps,seed=None):
    rng=Random(802 if seed is None else seed)
    tree=BranchMesh()
    trunk_height=9.75

    def center(z):
        t=z/trunk_height
        return Vector((-.23*sin(1.14*t*tau)+.15*t,.31*sin(t*tau-.27)*t,z))

    levels=[trunk_height*t for t in (0,.011,.028,.060,.11,.183,.276,.397,.537,.654,.756,.864,.943)]
    rings=[]
    for z in levels:
        width=.534*(1-z/trunk_height)**.81
        ring=[]
        for i in range(20):
            angle=i*tau/20
            flare=.40*exp(-3.71*z)*max(cos(5*angle+.41),0)**3
            r=width*(1+.115*cos(3*angle+z*.51))+flare
            ring.append(tree.vertex(center(z)+Vector((r*cos(angle),r*sin(angle),0))))
        rings.append(ring)
    tree.cap(rings[0],center(0),0,-.081,reverse=True)
    for i,(a,b) in enumerate(zip(rings,rings[1:])):
        tree.join(a,b,levels[i]*.43,levels[i+1]*.43)
    tree.cap(rings[-1],center(trunk_height),levels[-1]*.43,trunk_height*.43)

    for tier in range(10):
        f=tier/9
        num=4 if tier<6 else 3
        for i in range(num):
            angle=tier*1.65+i*tau/num+rng.uniform(-.23,.23)
            ray=Vector((cos(angle),sin(angle),0))
            side=UP.cross(ray)
            z=trunk_height*(.217+.658*f)+rng.uniform(-.14,.21)
            start=center(z)
            spread=(2.28+2.8*sin(np.pi*(.22+.72*f)))*rng.uniform(.71,1.13)
            width=.226*(1-.89*f)*rng.uniform(.72,1.30)
            elbow=start+ray*spread*.37+UP*spread*rng.uniform(.19,.32)
            crook=start+ray*spread*.71+side*rng.uniform(-.30,.30)+UP*spread*rng.uniform(.30,.42)
            tip=start+ray*spread+UP*spread*rng.uniform(.28,.48)
            tree.shoot((start,elbow,crook,tip),(width,.64*width,.31*width),6,f*.83)
            sections=((start,elbow,.70),(elbow,crook,.14),(elbow,crook,.51),
                      (elbow,crook,.88),(crook,tip,.23),(crook,tip,.63))
            for row,(a,b,t) in enumerate(sections):
                joint=a.lerp(b,t)
                length=(.65+.115*spread)*rng.uniform(.75,1.25)
                for sign in (-1,1):
                    heading=ray*rng.uniform(.23,.65)+side*sign*rng.uniform(.52,1.06)+UP*rng.uniform(.37,.93)
                    arm=joint+heading.normalized()*length*.73
                    tree.shoot((joint,arm),(.23*width,),3,f+row*.13)
                    tree.spray(joint,heading,length,length*.92,rng.uniform(.93,1.4))
                    outward=heading+UP*.61+ray*.33
                    tree.spray(joint.lerp(arm,.51),outward,length*.81,length*.74,.91)
            tree.spray(crook.lerp(tip,.64),ray+UP*.74,1.03,.91,1.19)
    for i in range(11):
        angle=i*2.39996
        ray=Vector((cos(angle),sin(angle),0))
        tree.spray(center(trunk_height*(.79+.013*i)),ray+UP*.52,1.02,.83,1.03)

    bark=bark_swatch_maps(ASSETS/"deciduous"/"english-oak"/"source"/"bark_swatch.png")
    return finish(tree,maps,"English Oak",(("bark",(*bark,2.84)),("leaves",atlas("oak"))),
                  seed,((.75,1.22),(.76,1.23),(.77,1.22)))


def hawthorn_mesh(maps,seed=None):
    rng=Random(475 if seed is None else seed)
    tree=BranchMesh()
    for i in range(27):
        rank=(i/26)**.73
        angle=i*2.39996+rng.uniform(-.32,.32)
        ray=Vector((cos(angle),sin(angle),0))
        side=UP.cross(ray)
        base=ray*(.035+.21*rank)+side*rng.uniform(-.049,.049)
        rise=(2.31-1.13*rank)*rng.uniform(.83,1.20)
        span=(.46+.74*rank)*rng.uniform(.82,1.19)
        width=(.030-.018*rank)*rng.uniform(.74,1.18)
        path=(base,base+ray*.18*span+UP*.29*rise,base+ray*.43*span+UP*.57*rise,
              base+ray*.76*span+UP*.84*rise,base+ray*span+UP*rise)
        first=len(tree.positions)
        tree.shoot(path,(width,.77*width,.54*width,.31*width),5,i*.13)
        for p in tree.positions[first:first+5]:
            p.z=0
        for row,(a,b,t) in enumerate(((path[0],path[1],.91),(path[1],path[2],.26),
                                       (path[1],path[2],.76),(path[2],path[3],.32),
                                       (path[2],path[3],.79),(path[3],path[4],.61))):
            p=a.lerp(b,t)
            for sign in (-1,1):
                heading=ray*rng.uniform(.26,.67)+side*sign*rng.uniform(.48,.97)+UP*rng.uniform(.32,.82)
                span2=rng.uniform(.27,.57)*(1-.084*row)
                end=p+heading.normalized()*span2*.85
                tree.shoot((p,end),(.35*width,),4,row*.14)
                tree.spray(p.lerp(end,.21),heading,span2,span2*.86,1.28)
                tree.spray(p.lerp(end,.51),heading+UP*.66,span2*.68,span2*.61,1.10)
                if row>=2 and sign==1 and (row+i)%3==0:
                    stem=p.lerp(end,.75)
                    cluster=stem+heading.normalized()*.027-UP*.027
                    tree.shoot((stem,cluster),(.00172,),3,.14)
                    for k in range(4):
                        bearing=k*2.39996+i
                        needle=Vector((cos(bearing),sin(bearing),0))
                        origin=cluster+needle*rng.uniform(.010,.021)-UP*rng.uniform(.001,.017)
                        r=rng.uniform(.0039,.0065)
                        tree.shoot((cluster,origin+UP*r),(.00084,),3,.19)
                        radial_mesh(tree,origin,UP,((0,.62*r),(r,r)),5,2)
        tree.spray(path[-2].lerp(path[-1],.69),ray+UP,.37,.29,1.2)

    stems=stem_maps()
    bark=(np.clip(stems[0]*np.array((.91,1.02,.87)),0,1),*stems[1:])
    raw=granular_maps("fruit")
    fruit=(np.clip(raw[0]*np.array((1.09,.49,.85)),0,1),*raw[1:])
    return finish(tree,maps,"Common Hawthorn",
                  (("stems",bark),("leaves",atlas("hawthorn")),("fruit",fruit)),
                  seed,((.74,1.20),(.76,1.21),(.77,1.22)),smooth_kinds=(0,2))


def build(oak):
    slug,name,mesh,group,height,width=(
        ("english-oak","English oak",oak_mesh,"deciduous",10.5,12.3) if oak else
        ("common-hawthorn","Common hawthorn",hawthorn_mesh,"shrubs",2.4,3.7))
    shots=[(slug+"-full",(11,-17,10),(0,0,3.37 if oak else 2.83),
            13.2 if oak else 14.4,(850,750)),
           (slug+"-detail",(8,-13,8),(.24,-.2,3.22 if oak else 4.04),
            6.5,(850,700))]
    main(ASSETS/group/slug,mesh,name,shots,(width,width,height),height/7.2,23)

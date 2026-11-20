"""Generate wild dog rose and burnet rose bushes with seeded variation."""
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
from build_birch_heather import atlas, finish, stem_maps
from build_rowan_foxtail_daisy import granular_maps, radial_mesh


def rose_petals(burnet):
    v,u=np.mgrid[:SIZE,:SIZE]/SIZE
    fine=.55+.23*np.sin(tau*(28*u+3*v))+.12*np.cos(tau*(50*u-2*v))
    ribs=np.exp(-abs(np.sin(tau*(7*u+.15*np.sin(1.1*tau*v))))*13)
    edge=np.clip((abs(u-.5)+.41*(1-v))*1.31,0,1)
    base=np.clip((v-.73)*2.6,0,1)
    core=np.array((.94,.92,.852) if burnet else (.938,.744,.779))
    color=np.zeros((SIZE,SIZE,3))+core
    color+=(fine*.13+ribs*.023)[...,None]*np.array((.22,.19,.21))
    color-=edge[...,None]*np.array((.023,.025,.051) if burnet else (.029,.19,.138))
    color-=base[...,None]*np.array((.055,.088,.21) if burnet else (.020,.019,.13))
    height=.48+.093*ribs+.052*fine
    return np.clip(color,0,1),height,.66+.16*height,.91+.09*height,.69


def flower(tree, origin, heading, radius, rng):
    axis=heading.normalized()
    side=UP.cross(axis).normalized()
    up=axis.cross(side)
    cup=tree.vertex(origin)
    spin=rng.uniform(0,tau)
    outline=((.19,-.184),(.42,-.392),(.73,-.462),(.93,-.32),
             (1,0),(.93,.32),(.73,.462),(.42,.392),(.19,.184))
    for i in range(5):
        angle=spin+i*tau/5
        ray=side*cos(angle)+up*sin(angle)
        edge=axis.cross(ray)
        shape=rng.uniform(.90,1.13)
        twist=rng.uniform(-.068,.068)
        rim=[]
        for distal,across in outline:
            flare=.36*distal**1.49+.33*across**2
            rim.append(tree.vertex(origin+radius*(shape*ray*distal+edge*(across+twist*distal)+axis*flare)))
        center=tree.vertex(origin+radius*(ray*.52+axis*.10))
        uv=[(.5+across,distal) for distal,across in outline]
        for j in range(len(rim)-1):
            tree.face((center,rim[j],rim[j+1]),((.5,.52),uv[j],uv[j+1]),2)
        tree.face((cup,rim[0],center),((.5,0),uv[0],(.5,.52)),2)
        tree.face((cup,center,rim[-1]),((.5,0),(.5,.52),uv[-1]),2)

    pollen=radius*.24
    rows=((radius*.046,pollen*.77),(radius*.119,pollen),(radius*.183,pollen*.63))
    radial_mesh(tree,origin,axis,rows,8,3)


def rose_mesh(maps, seed, burnet):
    rng=Random((548 if burnet else 772) if seed is None else seed)
    name="Burnet Rose" if burnet else "Dog Rose"
    tree=BranchMesh()
    stem_count=29 if burnet else 23
    for i in range(stem_count):
        rank=(i/(stem_count-1))**.69
        angle=i*2.39996+rng.uniform(-.24,.28)
        ray=Vector((cos(angle),sin(angle),0))
        side=UP.cross(ray)
        base=ray*(.027+(.18 if burnet else .13)*rank)+side*rng.uniform(-.047,.047)
        rise=((.76-.30*rank) if burnet else (1.82-.99*rank))*rng.uniform(.84,1.17)
        span=((.18+.50*rank) if burnet else (.43+.79*rank))*rng.uniform(.82,1.15)
        width=rng.uniform(.0031,.0064) if burnet else rng.uniform(.0059,.0110)
        ratios=(0,.20,.44,.64,.83,1)
        path=[base+ray*span*t**1.53+side*(.13*span*sin(t*2.21))+UP*(rise*sin(t*(1.78 if burnet else 1.97)))
              for t in ratios]
        length_factors=(1,.87,.66,.44,.28)
        first=len(tree.positions)
        tree.shoot(path,tuple(width*f for f in length_factors),5,i*.19)
        for position in tree.positions[first:first+5]:
            position.z=0

        for j,(a,b) in enumerate(zip(path,path[1:])):
            position=a.lerp(b,.55)
            sign=1 if (j+i)%2 else -1
            bend=-ray*.49+side*sign*.92+UP*.49
            spike=width*(2.2 if burnet else 1.95)
            tree.shoot((position,position+bend*spike),(.51*width,),3,.42)
            if j==0:
                continue
            for flank in (-1,1):
                axis=ray*rng.uniform(.43,.81)+side*flank*rng.uniform(.52,1.07)+UP*rng.uniform(.03,.61)
                scale=(rng.uniform(.112,.217) if burnet else rng.uniform(.173,.320))*(1-.094*j+.08*rank)
                stalk=position+axis.normalized()*scale*.73
                tree.shoot((position,stalk),(.22*width,),3,j*.29)
                tree.spray(position,axis,scale,scale*.72,1.17)
                if j in (2,3):
                    tree.spray(position.lerp(stalk,.25),axis+UP*.69,scale*.68,scale*.68,.89)

        flower_sites=(path[2].lerp(path[3],.74),path[3].lerp(path[4],.57),path[4].lerp(path[5],.78))
        for j,origin in enumerate(flower_sites):
            if (i+2*j)%5==0:
                continue
            sign=1 if (i+j)%2 else -1
            heading=(UP+rng.uniform(.42,.87)*ray+sign*rng.uniform(.29,.58)*side)
            length=rng.uniform(.036,.096) if burnet else rng.uniform(.052,.127)
            tip=origin+heading.normalized()*length
            tree.shoot((origin,tip),(.0021 if burnet else .0026,),3,.34)
            radius=rng.uniform(.021,.0305) if burnet else rng.uniform(.027,.040)
            flower(tree,tip,heading,radius,rng)

    stems=stem_maps()
    tone=np.array((.79,1.29,.72))
    return finish(tree,maps,name,
                  (("canes",(np.clip(stems[0]*tone,0,1),*stems[1:])),
                   ("leaves",atlas("rose")),("petals",rose_petals(burnet)),
                   ("pollen",granular_maps("disc"))),
                  seed,((.79,1.19),(.79,1.20),(.78,1.23)),smooth_kinds=(0,2,3))


def build(burnet):
    slug="burnet-rose" if burnet else "dog-rose"
    name="Burnet rose" if burnet else "Dog rose"
    size=.87 if burnet else 1.84
    span=1.76 if burnet else 2.87
    shots=[(slug+"-full",(11,-17,10),(0,0,3.05),15.5 if burnet else 13.3,(850,750)),
           (slug+"-detail",(8,-11,9),(-.15,-.30,4.16),6.25,(850,700))]
    main(ASSETS/"shrubs"/slug,lambda maps,seed:rose_mesh(maps,seed,burnet),name,shots,
         reference_size=(span,span,size),studio_scale=size/7.2,samples=24)

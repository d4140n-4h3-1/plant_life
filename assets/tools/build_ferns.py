"""Shared frond generator for hard fern and bracken."""
from math import cos, sin, tau
from pathlib import Path
from random import Random
import sys

import numpy as np
from mathutils import Vector

ASSETS = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ASSETS/"conifers"/"tools"))
from build_fir_larch import BranchMesh, UP
from build_pine import SIZE, main
from build_birch_heather import finish, stem_maps


def fern_atlas(bracken):
    """Generate a pinna with a cutout margin, midrib, veins and color variation."""
    yy,xx=np.mgrid[:SIZE,:SIZE]
    rgba=np.zeros((SIZE,SIZE,4))
    rgba[..., :3]=(.19,.31,.075)
    relief=np.full((SIZE,SIZE),.5)
    rng=Random(98 if bracken else 307)

    def leaflet(root,tip,breadth,color,teeth):
        root,tip=np.asarray(root),np.asarray(tip)
        axis=tip-root
        distance=np.linalg.norm(axis)
        direction=axis/distance
        along=((xx-root[0])*direction[0]+(yy-root[1])*direction[1])/distance
        length=np.clip(along,0,1)
        across=(xx-root[0])*direction[1]-(yy-root[1])*direction[0]
        width=breadth*np.sin(np.pi*length)**.72*(1.17-.33*length)
        width+=teeth*np.sin(np.pi*length)**.4*np.cos(24*tau*length)
        inner=width-abs(across)
        alpha=np.clip(inner+.5,0,1)*((along>0)&(along<1))
        midrib=np.exp(-abs(across)/max(1,breadth*.071))
        rib=np.exp(-13*abs(np.sin(tau*(8.5*length+abs(across)/breadth*.99))))*(1-midrib)
        grain=.5+.5*np.cos(xx*.56+yy*.36+np.sin(yy*.41))
        tint=.74+.15*length+.18*midrib+.12*rib+.078*grain
        covered=alpha>0
        rgba[..., :3][covered]=tint[covered,None]*color
        rgba[..., 3]=np.maximum(rgba[..., 3],alpha)
        relief[covered]=.55+.12*midrib[covered]+.05*rib[covered]+.052*grain[covered]

    if bracken:
        green=np.array((.266,.405,.109))
        for i in range(13):
            p=np.array((255.,469-i*30))
            extent=181*(1-i/14)**.87
            for side in (-1,1):
                length=extent*rng.uniform(.87,1.12)
                tip=p+np.array((side*length,-length*.43-8))
                leaflet(p,tip,max(9,length*.19),green*rng.uniform(.79,1.18),2.4)
        leaflet((255,500),(259,7),5,np.array((.355,.456,.19)),.65)
    else:
        leaflet((255,494),(258,19),156,np.array((.228,.438,.125)),2.2)
    return rgba,relief,.64+.15*relief,.90+.09*relief,.71


def make_fern(maps,seed,bracken):
    rng=Random((509 if bracken else 210) if seed is None else seed)
    name="Bracken" if bracken else "Hard Fern"
    mesh=BranchMesh()

    def pinna(origin, heading, length, breadth):
        axis=heading.normalized()
        side=UP.cross(axis).normalized()
        normal=axis.cross(side)
        turn=rng.uniform(-.27,.27)
        edge=(side*cos(turn)+normal*sin(turn))*breadth*.5
        middle=origin+axis*length*.56+normal*.059*length
        end=origin+axis*length
        rings=[(mesh.vertex(p-edge),mesh.vertex(p+edge)) for p in (origin,middle,end)]
        for i,((a,b),(d,c)) in enumerate(zip(rings,rings[1:])):
            v0,v1=i*.5,(i+1)*.5
            mesh.face((a,b,c),((0,v0),(1,v0),(1,v1)),1)
            mesh.face((a,c,d),((0,v0),(1,v1),(0,v1)),1)

    for i in range(8 if bracken else 17):
        angle=i*2.39996+rng.uniform(-.29,.29)
        ray=Vector((cos(angle),sin(angle),0))
        side=UP.cross(ray)
        rank=i/(7 if bracken else 16)
        height=(.81-.27*rank if bracken else .43-.19*rank)*rng.uniform(.87,1.15)
        span=(.32+.27*rank if bracken else .12+.34*rank)*rng.uniform(.84,1.15)
        base=ray*rng.uniform(.014,.100 if bracken else .052)
        drop=rng.uniform(.04,.14 if bracken else .19)

        def rachis(t):
            if bracken:
                return base+ray*span*(.17*t+.83*t**2.1)+UP*(height*sin(2.01*t)-drop*t**3)
            return base+ray*span*(.24*t+.76*t**1.46)+UP*(height*sin(2.1*t)-drop*t**3)

        path=tuple(rachis(t) for t in (0,.17,.34,.53,.70,.86,1))
        width=rng.uniform(.0031,.0057) if bracken else rng.uniform(.0017,.0029)
        first=len(mesh.positions)
        mesh.shoot(path,tuple(width*f for f in (1,.88,.71,.55,.40,.26)),4,rng.random())
        for p in mesh.positions[first:first+4]:
            p.z=0
        pairs=10 if bracken else 18
        start=.43 if bracken else .16
        for row in range(pairs):
            progress=row/(pairs-1)
            t=start+(1-start)*(.046+.875*progress)
            central=rachis(t)
            if bracken:
                span_factor=(1-progress)**.92
                length=(.059+.281*span_factor)*rng.uniform(.91,1.13)
                breadth=length*.62
            else:
                silhouette=sin(np.pi*(.14+.83*progress))**.78
                length=(.014+.089*silhouette)*(1-.26*rank)*rng.uniform(.92,1.08)
                breadth=.013+.012*silhouette
            for sign in (-1,1):
                direction=(side*sign+ray*(.36+.61*progress)
                           +UP*rng.uniform(-.25,.29))
                pinna(central,direction,length,breadth)
        pinna(rachis(.92),rachis(1)-rachis(.92),.039 if bracken else .026,
              .020 if bracken else .013)

    stem=stem_maps()
    stem_color=np.clip(stem[0]*np.array((.88,1.27,.68)),0,1)
    return finish(mesh,maps,name,(("rachis",(stem_color,*stem[1:])),("fronds",fern_atlas(bracken))),
                  seed,((.77,1.19),(.79,1.24),(.79,1.20)))


def build(bracken):
    folder="bracken" if bracken else "hard-fern"
    name="Bracken" if bracken else "Hard fern"
    asset=ASSETS/"ferns"/folder
    size=.79 if bracken else .46
    shots=[(folder+"-full",(10,-15,12),(0,0,2.7),14.6 if bracken else 17,(850,740)),
           (folder+"-detail",(8,-13,12),(0,0,3.25),8.2 if bracken else 9.0,(840,680))]
    main(asset,lambda maps,seed:make_fern(maps,seed,bracken),name,shots,
         reference_size=(1.1,1.1,size),studio_scale=size/7.2,samples=22)

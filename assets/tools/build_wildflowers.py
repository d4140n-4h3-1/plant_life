"""Shared detail atlas and Blender generators for foxglove and wood sorrel."""
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


def leaves(sorrel):
    v,u=np.mgrid[:SIZE,:SIZE]/(SIZE-1)
    t=1-v
    if sorrel:
        x=abs(u-.5+.013*np.sin(t*tau))
        main_width=.412*np.sin(np.pi*np.clip((t-.035)/.80,0,1))**.76
        base=main_width-x
        upper=1-((x-.23)/.222)**2-((t-.716)/.229)**2
        edge=np.where((t>.042)&(t<.965),np.maximum(base,upper*.29),-1)
        dark,light=np.array((.15,.32,.109)),np.array((.328,.50,.161))
    else:
        x=abs(u-.5+.024*np.sin(1.1*tau*t))
        l=np.clip((t-.025)/.95,0,1)
        blade=.43*np.sin(np.pi*l)**.79*(1.11-.29*l)
        teeth=.018*np.cos(36*tau*l)*np.sin(np.pi*l)**.42
        edge=blade+teeth-x
        edge=np.where((t>.025)&(t<.975),edge,-1)
        dark,light=np.array((.134,.292,.115)),np.array((.32,.42,.172))

    ribs=np.exp(-12*abs(np.sin(tau*(7.5*t+x*1.2+.035*np.sin(tau*x)))))
    midrib=np.exp(-90*x)
    fine=np.random.default_rng(98).random(x.shape)
    radiance=np.clip(.31+.22*np.sin(3*tau*t)+.22*np.cos(tau*(u-t))+.16*ribs+.25*midrib+.18*fine,0,1)
    color=dark+radiance[...,None]*(light-dark)
    height=.48+.15*midrib+.075*ribs+.047*fine
    alpha=np.clip(edge*150+.51,0,1)
    return np.concatenate((color,alpha[...,None]),axis=-1),height,.66+.14*height,.90+.10*height,.84


def flower_maps(sorrel):
    v,u=np.mgrid[:SIZE,:SIZE]/SIZE
    fine=.5+.5*np.sin(tau*(30*u+2*v+.09*np.sin(12*tau*v)))
    if sorrel:
        veins=np.exp(-abs(np.sin(tau*(4*u+.08*np.sin(tau*v))))*15)
        throat=np.clip((v-.71)*3.8,0,1)
        tint=veins*(.32+.68*v)
        color=np.zeros((SIZE,SIZE,3))+np.array((.94,.895,.849))
        color-=tint[...,None]*np.array((.11,.24,.15))
        color-=throat[...,None]*np.array((.019,.062,.34))
        height=.48+.13*veins+.043*fine
    else:
        panel=u>=.5
        a=np.mod(u*2,1)
        grooves=.5+.5*np.cos(tau*(8*a+.12*np.sin(1.9*tau*v)))
        mottles=np.zeros_like(v)
        rng=Random(348)
        for _ in range(53):
            x,y=rng.uniform(.04,.97),rng.uniform(.13,.74)
            dx=abs(a-x)
            dot=(np.minimum(dx,1-dx)/rng.uniform(.012,.031))**2+((v-y)/rng.uniform(.010,.031))**2
            mottles=np.maximum(mottles,np.exp(-dot*2.1))
        outer=np.zeros((SIZE,SIZE,3))+np.array((.66,.284,.461))
        outer+=(.095*grooves+.054*fine+.065*v)[...,None]*np.array((.91,.55,.82))
        inner=np.zeros_like(outer)+np.array((.84,.59,.713))
        inner-=(mottles*.77)[...,None]*np.array((.52,.44,.47))
        color=np.where(panel[...,None],inner,outer)
        height=.50+.06*grooves+.055*fine+.10*mottles*panel
    return color,height,.58+.18*height,.89+.11*height,.58


def blade(tree, root, direction, length, width, roll=0):
    axis=direction.normalized()
    side=UP.cross(axis).normalized()
    normal=axis.cross(side)
    edge=width*.5*(side*cos(roll)+normal*sin(roll))
    spine=(root,root+axis*length*.48+normal*length*.13,root+axis*length)
    rings=[(tree.vertex(p-edge),tree.vertex(p+edge)) for p in spine]
    for i,((a,b),(d,c)) in enumerate(zip(rings,rings[1:])):
        v0,v1=i*.5,(i+1)*.5
        tree.face((a,b,c),((0,v0),(1,v0),(1,v1)),1)
        tree.face((a,c,d),((0,v0),(1,v1),(0,v1)),1)


def ground_stem(tree, path, widths):
    first=len(tree.positions)
    tree.shoot(path,widths,5,0)
    for p in tree.positions[first:first+5]:
        p.z=0


def bell(tree, root, heading, length, width):
    direction=heading.normalized()
    side=UP.cross(direction).normalized()
    up=direction.cross(side)
    rings=[]
    for level,radius,size in ((0,.22,1),(.23,.47,1),(.59,.75,1),
                               (.94,1,1),(.98,.83,1),(.68,.59,.91),(.27,.28,.85)):
        center=root+direction*length*level-UP*(.17*length*level**2)
        ring=[]
        for i in range(9):
            angle=i*tau/9
            waviness=1+.071*cos(5*angle)*level
            r=width*radius*waviness
            ring.append(tree.vertex(center+r*(cos(angle)*side+sin(angle)*size*up)))
        rings.append(ring)

    # The last three rows run back down the throat, creating a real open lip.
    along=(.02,.22,.52,.94,.945,.61,.23)
    for i,(a,b) in enumerate(zip(rings,rings[1:])):
        index=len(tree.uvs)
        tree.join(a,b,along[i],along[i+1],2)
        band=0 if i<4 else .50
        for row in range(index,len(tree.uvs)):
            tree.uvs[row]=tuple((band+.006+.485*u,v) for u,v in tree.uvs[row])
    tree.cap(rings[0],root-direction*.002,.03,.001,2,reverse=True)
    index=len(tree.uvs)
    tree.cap(rings[-1],root+direction*.19*length,.22,.17,2)
    for row in range(index,len(tree.uvs)):
        tree.uvs[row]=tuple((.506+.485*u,v) for u,v in tree.uvs[row])


def foxglove_mesh(maps,seed=None):
    rng=Random(113 if seed is None else seed)
    tree=BranchMesh()
    for i in range(27):
        angle=i*2.39996+rng.uniform(-.22,.22)
        ray=Vector((cos(angle),sin(angle),0))
        rank=i/26
        root=ray*rng.uniform(.014,.074)+UP*rng.uniform(.035,.119)
        heading=ray+UP*rng.uniform(.07,.61)
        length=rng.uniform(.195,.342)*(1-.28*rank)
        blade(tree,root,heading,length,length*rng.uniform(.34,.54),rng.uniform(-.42,.42))

    for stem in range(3):
        angle=stem*2.39996+.22
        ray=Vector((cos(angle),sin(angle),0))
        side=UP.cross(ray)
        base=ray*(.023+.047*stem)
        rise=(1.39-.18*stem)*rng.uniform(.91,1.11)
        lean=rng.uniform(.08,.19)*(1+.28*stem)
        ratios=(0,.18,.38,.57,.73,.87,.97,1)
        path=[base+ray*lean*t*t+UP*rise*t for t in ratios]
        ground_stem(tree,path,(.0101,.0084,.0071,.0059,.0048,.0034,.0020))

        def axis(t):
            j=next(k for k in range(len(ratios)-1) if ratios[k+1]>=t)
            return path[j].lerp(path[j+1],(t-ratios[j])/(ratios[j+1]-ratios[j]))

        for j in range(8):
            pos=j/8
            phase=j*2.39996+angle
            beam=Vector((cos(phase),sin(phase),.32))
            length=(.235-.078*pos)*rng.uniform(.79,1.10)
            blade(tree,axis(.09+.43*pos),beam,length,length*.42,rng.uniform(-.71,.71))

        for j in range(19):
            t=.489+.0254*j
            p=axis(t)
            progress=j/18
            sway=rng.uniform(-.46,.46)
            heading=ray*(.54+.49*sin(j*1.28))+side*(.67*cos(j*1.14)+sway)-UP*rng.uniform(.30,.82)
            facing=heading.normalized()
            root=p+facing*rng.uniform(.020,.037)+UP*.008
            tree.shoot((p,root),(.0021,),4,.24)
            length=(.064-.035*progress)*rng.uniform(.90,1.18)
            bell(tree,root,heading,length,length*rng.uniform(.30,.38))
    stalk=stem_maps()
    stalk=(np.clip(stalk[0]*np.array((.80,1.29,.67)),0,1),*stalk[1:])
    return finish(tree,maps,"Foxglove",(("stems",stalk),("leaves",leaves(False)),("bells",flower_maps(False))),
                  seed,((.79,1.20),(.80,1.19),(.78,1.24)), smooth_kinds=(0,2))


def petalled_flower(tree, origin, direction, radius, spin):
    axis=direction.normalized()
    right=UP.cross(axis).normalized()
    forward=axis.cross(right)
    cup=tree.vertex(origin+axis*radius*.04)
    for j in range(5):
        angle=spin+j*tau/5
        stem=right*cos(angle)+forward*sin(angle)
        tangent=axis.cross(stem)
        outline=((.23,-.19),(.61,-.28),(.87,-.23),(1,0),(.87,.23),(.61,.28),(.23,.19))
        rim=[]
        for along, across in outline:
            bowl=.32*along+.26*across**2
            rim.append(tree.vertex(origin+radius*(stem*along+tangent*across+axis*bowl)))
        center=tree.vertex(origin+radius*(stem*.56+axis*.12))
        uvs=[(.5+across*1.5,along) for along,across in outline]
        for k in range(len(rim)-1):
            tree.face((center,rim[k],rim[k+1]),((.5,.56),uvs[k],uvs[k+1]),2)
        tree.face((cup,rim[0],center),((.5,0),uvs[0],(.5,.56)),2)
        tree.face((cup,center,rim[-1]),((.5,0),(.5,.56),uvs[-1]),2)


def sorrel_mesh(maps,seed=None):
    rng=Random(148 if seed is None else seed)
    tree=BranchMesh()
    for i in range(43):
        angle=i*2.39996+rng.uniform(-.25,.25)
        ray=Vector((cos(angle),sin(angle),0))
        rank=(i/42)**.57
        root=ray*rng.uniform(.025+.075*rank,.083+.079*rank)
        rise=(.114-.060*rank)*rng.uniform(.77,1.24)
        lean=rng.uniform(.025,.067)
        top=root+ray*lean+UP*rise
        ground_stem(tree,(root,root+ray*lean*.41+UP*rise*.59,top),(.0015,.0010))
        spin=angle+rng.uniform(-.48,.48)
        for j in range(3):
            bearing=spin+j*tau/3
            direction=Vector((cos(bearing),sin(bearing),rng.uniform(-.21,.32)))
            length=rng.uniform(.022,.043)*(1-.18*rank)
            blade(tree,top,direction,length,length*rng.uniform(.83,1.10),rng.uniform(-.27,.27))

    for i in range(12):
        angle=i*2.39996+1.25
        ray=Vector((cos(angle),sin(angle),0))
        root=ray*rng.uniform(.027,.112)
        rise=rng.uniform(.098,.192)
        bow=rng.uniform(.025,.063)
        tip=root+ray*bow+UP*rise
        ground_stem(tree,(root,root+ray*bow*.48+UP*(rise*.67),tip),(.00131,.00092))
        petalled_flower(tree,tip,UP+ray*rng.uniform(.30,.56),rng.uniform(.0091,.0149),rng.uniform(0,tau))
    stalk=stem_maps()
    stalk=(np.clip(stalk[0]*np.array((.85,1.39,.73)),0,1),*stalk[1:])
    return finish(tree,maps,"Wood Sorrel",(("stems",stalk),("leaves",leaves(True)),("petals",flower_maps(True))),
                  seed,((.79,1.20),(.79,1.22),(.77,1.22)), smooth_kinds=(0,2))


def build(sorrel):
    if sorrel:
        folder,name,size,mesh="wood-sorrel","Wood sorrel",.19,sorrel_mesh
        shots=[("sorrel-full",(10,-16,15),(0,0,2.25),20.4,(850,730)),
               ("sorrel-detail",(8,-13,15),(.66,-.3,3.32),9.3,(850,700))]
    else:
        folder,name,size,mesh="foxglove","Foxglove",1.43,foxglove_mesh
        shots=[("foxglove-full",(12,-18,9),(0,0,3.07),9.5,(790,870)),
               ("foxglove-detail",(8,-13,7.2),(.14,0,5.93),3.43,(850,710))]
    main(ASSETS/"wildflowers"/folder,mesh,name,shots,
         reference_size=(3*size,3*size,size),studio_scale=size/7.2,samples=24)

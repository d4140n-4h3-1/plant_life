"""Geometry and foliage atlases for silver birch and flowering heather."""
from math import cos, exp, sin, tau
from pathlib import Path
from random import Random
import sys

import bpy
import numpy as np
from mathutils import Vector

ASSETS = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ASSETS/"conifers"/"tools"))
from build_fir_larch import BranchMesh, UP
from build_pine import SIZE, bark_swatch_maps, main, material

BIRCH = ASSETS/"deciduous"/"silver-birch"
HEATHER = ASSETS/"shrubs"/"common-heather"
BROOM = ASSETS/"shrubs"/"common-broom"


def atlas(kind):
    """Paint a single branched spray with a cutout silhouette."""
    rng = Random(162 if kind=="leaves" else 341)
    rgba=np.zeros((SIZE,SIZE,4))
    birch=kind=="leaves"
    broom=kind in ("broom-leaves","broom-flowers")
    rgba[..., :3]=(.19,.32,.11) if kind!="blossoms" else (.43,.23,.33)
    if kind=="broom-flowers":
        rgba[..., :3]=(.58,.45,.09)
    height=np.full((SIZE,SIZE),.5)
    stem=np.array((.31,.26,.14))

    def mark(start,end,width,color,leaf=False):
        start,end=np.array(start),np.array(end)
        radius=int(width)+3
        x0=max(0,int(min(start[0],end[0]))-radius)
        x1=min(SIZE,int(max(start[0],end[0]))+radius)
        y0=max(0,int(min(start[1],end[1]))-radius)
        y1=min(SIZE,int(max(start[1],end[1]))+radius)
        if x0>=x1 or y0>=y1:
            return
        y,x=np.mgrid[y0:y1,x0:x1]
        d=end-start
        length=np.linalg.norm(d)
        t=((x-start[0])*d[0]+(y-start[1])*d[1])/length**2
        q=np.clip(t,0,1)
        lateral=abs((x-start[0])*d[1]-(y-start[1])*d[0])/length
        if leaf:
            rim=width*np.sin(np.pi*q)**.83*(1.23-.47*q)
            rim+=min(1.9,width*.21)*np.cos(19*tau*q)*np.sin(np.pi*q)**.4
            alpha=np.clip(rim-lateral+.55,0,1)*((t>0)&(t<1))
            midrib=np.exp(-lateral/max(1,width*.077))
            veins=np.exp(-abs(np.sin(tau*(q*5+lateral/max(1,width)*.78)))*9)*(1-midrib)
            tone=.76+.16*midrib+.12*veins+.19*q+.08*np.sin(x*.61+y*.43)
        else:
            distance=np.hypot(x-start[0]-d[0]*q,y-start[1]-d[1]*q)
            alpha=np.clip(width*(1-.52*q)-distance+.55,0,1)
            tone=.81+.27*q+.15*np.clip(1-lateral/width,0,1)
        mask=alpha>0
        ref=rgba[y0:y1,x0:x1]
        ref[..., :3][mask]=tone[mask,None]*color
        ref[..., 3]=np.maximum(ref[..., 3],alpha)
        height[y0:y1,x0:x1][mask]=.5+alpha[mask]*.21

    root=np.array((254.,492.))
    top=np.array((259.,25.))
    shoots=[(root,top)]
    for i in range(7 if broom else 9 if birch else 13):
        y=441-i*(56 if broom else 43 if birch else 29)
        for sign in (-1,1):
            start=np.array((256.,y+rng.uniform(-12,12)))
            span=(145-7*i) if birch else (130-4*i)
            shoots.append((start,start+np.array((sign*span*rng.uniform(.65,1.16),-rng.uniform(39,95)))))
    for start,end in reversed(shoots):
        direction=(end-start)/np.linalg.norm(end-start)
        lateral=np.array((-direction[1],direction[0]))
        central=np.linalg.norm(end-start)>300
        mark(start,end,2.9,stem)
        count=(19 if central else 4) if broom else (13 if central else 6) if birch else (27 if central else 14)
        for i in range(count):
            p=start+(end-start)*(i+.44)/count
            sign=-1 if i%2 else 1
            if birch:
                blade=rng.uniform(25,55)*(1-.16*i/count)
                heading=direction*rng.uniform(.25,.75)+sign*lateral*rng.uniform(.65,1.07)
                color=np.array((.246,.433,.126))*rng.uniform(.78,1.25)
                mark(p,p+heading*blade,blade*.43,color,leaf=True)
            elif broom:
                p=p+sign*lateral*3
                if kind=="broom-leaves" or i%4==0:
                    for finger in (-1,0,1):
                        heading=direction*.79+lateral*(sign*.53+finger*.52)
                        tip=p+heading*rng.uniform(10,23)
                        mark(p,tip,rng.uniform(3,6),np.array((.29,.415,.124))*rng.uniform(.81,1.12),leaf=True)
                else:
                    heading=direction*.46+lateral*sign*.87
                    pedicel=p+heading*9
                    mark(p,pedicel,2.0,stem)
                    sepia=np.array((.76,.47,.046))*rng.uniform(.91,1.15)
                    yellow=np.array((.95,.77,.10))*rng.uniform(.91,1.08)
                    for lobe in (-1,0,1):
                        fan=heading+lateral*lobe*.26+direction*lobe*.24
                        mark(pedicel,pedicel+fan*rng.uniform(15,21),rng.uniform(5.7,8.9),sepia,leaf=True)
                    mark(pedicel+heading*3,pedicel+heading*19+direction*5,7.6,yellow,leaf=True)
            elif kind=="greenery" or i<int(count*.35):
                blade=rng.uniform(9.5,17.0) if kind=="greenery" else rng.uniform(6.2,12.0)
                color=np.array((.188,.288,.13))*rng.uniform(.72,1.21)
                mark(p,p+(direction*.91+sign*lateral*.68)*blade,3.5 if kind=="greenery" else 2.5,color,leaf=True)
            else:
                base=p+lateral*sign*rng.uniform(3,8)
                center=base+direction*4
                petal=np.array((.60,.29,.49))*rng.uniform(.84,1.23)
                for j in range(4):
                    angle=j*tau/4+rng.uniform(-.25,.25)
                    q=center+np.array((cos(angle),sin(angle)))*rng.uniform(2.8,5.1)
                    mark(center,q,rng.uniform(2.3,3.65),petal)
                mark(base,center,1.5,np.array((.82,.54,.69)))
    return rgba,height,.69+.12*height,.89+.10*height,.58


def stem_maps():
    y,x=np.mgrid[:SIZE,:SIZE]/SIZE
    fiber=.5+.5*np.sin(tau*(21*x+y+.15*np.sin(3*tau*y)))
    patches=.50+.23*np.cos(tau*(9*x+2*y))
    color=np.array((.275,.187,.12))+(fiber*.40+patches*.60)[...,None]*np.array((.18,.19,.12))
    return color,.52+.17*fiber,.82+.09*patches,.87+.10*fiber,1.2


def finish(tree, maps, name, sources, seed, ranges):
    if seed is not None:
        rng=Random(f"{name}:{seed}")
        factors=[rng.uniform(*limits) for limits in ranges]
        max_height=max(p.z for p in tree.positions)
        drag=rng.uniform(-.055,.055)*max_height
        for i,(x,y,z) in enumerate(tree.positions):
            tree.positions[i]=(x*factors[0]+drag*(z/max_height)**1.7,y*factors[1],z*factors[2])
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(tree.positions,[],tree.faces)
    assert not mesh.validate()
    mesh.update()
    for kind,data in sources:
        mesh.materials.append(material(kind,maps,label=name,texture_data=data))
    uv_layer=mesh.uv_layers.new(name="UVMap")
    for poly, tex, kind in zip(mesh.polygons,tree.uvs,tree.kinds):
        poly.material_index=kind
        poly.use_smooth=kind==0
        for index,uv in zip(poly.loop_indices,tex):
            uv_layer.data[index].uv=uv
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj
    obj.select_set(True)
    if seed is not None:
        obj["plant_seed"]=str(seed)
    return obj


def birch_mesh(maps,seed=None):
    rng=Random(627 if seed is None else seed)
    tree=BranchMesh()
    h=12.7

    def center(z):
        t=z/h
        return Vector((.24*sin(.78*t*tau)+.10*t,.18*sin(1.2*t*tau)*t,z))

    trunk=[]
    levels=[h*s for s in (0,.009,.025,.051,.084,.144,.228,.34,.45,.57,.68,.78,.88,.956)]
    for z in levels:
        width=.199*(1-z/h)**.85
        ring=[]
        for i in range(16):
            angle=i*tau/16
            flare=.18*exp(-6*z)*max(cos(5*angle-.3),0)**3
            r=width*(1+.049*cos(3*angle+z*.8))+flare
            ring.append(tree.vertex(center(z)+Vector((cos(angle)*r,sin(angle)*r,0))))
        trunk.append(ring)
    tree.cap(trunk[0],center(0),0,-.1,reverse=True)
    for i,(first,second) in enumerate(zip(trunk,trunk[1:])):
        tree.join(first,second,levels[i]*.62,levels[i+1]*.62)
    tree.cap(trunk[-1],center(h),levels[-1]*.62,h*.62)

    for tier in range(13):
        f=tier/12
        z=h*(.238+.665*f)
        radial=.51+2.86*sin(np.pi*(.18+.79*f))**.81
        count=5 if tier<8 else 4
        for j in range(count):
            azimuth=tier*1.84+j*tau/count+rng.uniform(-.24,.24)
            ray=Vector((cos(azimuth),sin(azimuth),0))
            side=UP.cross(ray)
            origin=center(z+rng.uniform(-.22,.23))
            spread=radial*rng.uniform(.78,1.14)
            joint=origin+ray*spread*.49+UP*spread*.20
            outer=origin+ray*spread*.78+UP*spread*.28
            tip=origin+ray*spread+UP*spread*rng.uniform(.04,.22)
            thickness=.061*(1-.86*f)*rng.uniform(.86,1.16)
            tree.shoot((origin,joint,outer,tip),(thickness,.52*thickness,.23*thickness),5,rng.random())
            for row,(a,b) in enumerate(((origin,joint),(joint,outer),(outer,tip))):
                perch=a.lerp(b,.64)
                length=(.38+.30*spread)*(1-.13*row)*rng.uniform(.91,1.16)
                for sign in (-1,1):
                    heading=ray*rng.uniform(.40,1)+side*sign*rng.uniform(.56,1.13)-UP*rng.uniform(.25,.76)
                    fork=perch+heading.normalized()*length*.74
                    tree.shoot((perch,fork),(.22*thickness,),3,f)
                    tree.spray(perch,heading,length,length*.86,1.08)
                    tree.spray(perch.lerp(fork,.29),heading+ray*.46+UP*.48,
                               length*.72,length*.53,.91)
            tree.spray(outer.lerp(tip,.6),ray-UP*.34,.36+.2*spread,.35+.16*spread,1.32)
    for j in range(8):
        angle=j*tau/8
        tree.spray(center(11.4+j*.08),Vector((cos(angle),sin(angle),.77)),.72,.58,1.12)
    bark=bark_swatch_maps(BIRCH/"source"/"bark_swatch.png")
    return finish(tree,maps,"Silver Birch",(("bark",(*bark,2.45)),("leaves",atlas("leaves"))),
                  seed,((.81,1.19),(.80,1.20),(.78,1.20)))


def heather_mesh(maps,seed=None):
    rng=Random(407 if seed is None else seed)
    tree=BranchMesh()
    for stem in range(42):
        index=(stem/41)**.58
        angle=2.39996*stem+rng.uniform(-.38,.38)
        ray=Vector((cos(angle),sin(angle),0))
        side=UP.cross(ray)
        base=ray*(.011+.11*index)
        reach=(.09+.28*index)*rng.uniform(.81,1.16)
        rise=(.48-.25*index)*rng.uniform(.84,1.16)
        elbow=base+ray*reach*.47+UP*rise*.37
        top=base+ray*reach+UP*rise
        branch_size=rng.uniform(.0014,.0028)
        start=len(tree.positions)
        tree.shoot((base,elbow,top),(branch_size,branch_size*.53),4,2*index)
        for v in tree.positions[start:start+4]:
            v.z=0
        for j in range(2):
            root=(base.lerp(elbow,.90) if j==0 else elbow.lerp(top,.21))
            direction=ray*.80+side*(-.69 if j==0 else .61)+UP*.41
            material_start=len(tree.kinds)
            tree.spray(root,direction,.106+reach*.13,.067+reach*.046,1.18)
            tree.kinds[material_start:]=[1]*4
        for j,f in enumerate((.14,.39,.65,.87)):
            joint=elbow.lerp(top,f)
            turn=side*(1 if j%2 else -1)
            heading=ray*.49+turn*rng.uniform(.45,.77)+UP*rng.uniform(.45,1.15)
            length=rng.uniform(.081,.147)*(1-.27*f)
            material_start=len(tree.kinds)
            tree.spray(joint,heading,length,.68*length,.86)
            kind=2 if (stem+j*3)%7>2 else 1
            tree.kinds[material_start:]=[kind]*4
        material_start=len(tree.kinds)
        tree.spray(elbow.lerp(top,.67),ray*.41+UP,.13+rise*.11,.077+rise*.058,1.29)
        tree.kinds[material_start:]=[2]*4
    return finish(tree,maps,"Common Heather",
                  (("stems",stem_maps()),("greenery",atlas("greenery")),("blossoms",atlas("blossoms"))),
                  seed,((.74,1.24),(.74,1.25),(.76,1.21)))


def build_birch():
    shots=[("birch-full",(10,-17,7.4),(0,0,3.46),8.85,(740,880)),
           ("birch-detail",(-9,-13,6.5),(.12,0,3.34),4.54,(820,680))]
    main(BIRCH,birch_mesh,"Silver birch",shots,(7.6,7.6,12.7),12.7/7.2,22)


def build_heather():
    shots=[("heather-full",(12,-17,11),(0,0,2.4),16.8,(850,740)),
           ("heather-detail",(8,-14,9),(-.78,1.1,3.7),7.0,(820,680))]
    main(HEATHER,heather_mesh,"Common heather",shots,(.86,.86,.56),.56/7.2,22)



def broom_mesh(maps, seed=None):
    rng=Random(728 if seed is None else seed)
    tree=BranchMesh()
    for index in range(32):
        rank=(index/31)**.62
        angle=2.39996*index+rng.uniform(-.29,.29)
        ray=Vector((cos(angle),sin(angle),0))
        side=UP.cross(ray)
        base=ray*(.017+.14*rank)
        spread=(.22+.74*rank)*rng.uniform(.82,1.17)
        rise=(1.53-.77*rank)*rng.uniform(.81,1.21)
        elbow=base+ray*.31*spread+UP*.39*rise
        shoulder=base+ray*.72*spread+UP*.77*rise
        top=base+ray*spread+UP*rise+side*rng.uniform(-.13,.13)
        thickness=rng.uniform(.0041,.0091)
        first=len(tree.positions)
        tree.shoot((base,elbow,shoulder,top),(thickness,.67*thickness,.36*thickness),5,index*.19)
        for v in tree.positions[first:first+5]:
            v.z=0
        for row,(a,b,t) in enumerate(((base,elbow,.87),(elbow,shoulder,.24),
                                      (elbow,shoulder,.71),(shoulder,top,.19),
                                      (shoulder,top,.60),(shoulder,top,.87))):
            joint=a.lerp(b,t)
            sign=1 if (row+index)%2 else -1
            heading=ray*rng.uniform(.33,.77)+side*sign*rng.uniform(.23,.79)+UP*rng.uniform(.61,1.22)
            length=rng.uniform(.24,.43)*(1-.068*row)
            fork=joint+heading.normalized()*length*.78
            tree.shoot((joint,fork),(.23*thickness,),3,index*.19+row*.16)
            face=len(tree.kinds)
            tree.spray(joint,heading,length,length*.61,1.12)
            if row>=2 and (index+row)%5!=0:
                tree.kinds[face:]=[2]*4
            if row in (1,3):
                face=len(tree.kinds)
                tree.spray(joint.lerp(fork,.36),heading-side*sign*.55,length*.63,length*.40,1.23)
                if row==3:
                    tree.kinds[face:]=[2]*4
        face=len(tree.kinds)
        tree.spray(shoulder.lerp(top,.55),ray*.51+UP,.25,.145,.95)
        tree.kinds[face:]=[2]*4

    stems=stem_maps()
    green_shoots=(np.clip(stems[0]*np.array((.80,1.27,.77)),0,1),*stems[1:])
    return finish(tree,maps,"Common Broom",
                  (("stems",green_shoots),("leaves",atlas("broom-leaves")),("flowers",atlas("broom-flowers"))),
                  seed,((.75,1.23),(.76,1.24),(.77,1.20)))


def build_broom():
    shots=[("broom-full",(12,-17,10),(0,0,2.97),12.9,(850,750)),
           ("broom-detail",(8,-14,8),(0,0,3.87),6.3,(850,700))]
    main(BROOM,broom_mesh,"Common broom",shots,(2.40,2.40,1.68),1.68/7.2,24)

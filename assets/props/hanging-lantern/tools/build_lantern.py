"""Build an animated hanging lantern, a portable GLB, and previews."""
import argparse
import json
from math import cos, radians, sin, tau
from pathlib import Path
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory

import bmesh
import bpy
from mathutils import Quaternion, Vector

ASSET=Path(__file__).resolve().parents[1]
PERIOD=96
FPS=24


def light_optional(path):
    """Leave KHR_lights_punctual in the GLB's extensionsUsed, but not extensionsRequired.

    Blender's exporter marks the light extension as required. Then an importer that does not read
    lights refuses to load the model. The light is an optional extra for those importers.
    """
    data=Path(path).read_bytes()
    length=struct.unpack_from("<I",data,12)[0]
    doc=json.loads(data[20:20+length])
    required=[name for name in doc.get("extensionsRequired",[]) if name!="KHR_lights_punctual"]
    if required:
        doc["extensionsRequired"]=required
    else:
        doc.pop("extensionsRequired",None)
    chunk=json.dumps(doc,separators=(",",":")).encode()
    chunk+=b" "*(-len(chunk)%4)
    rest=data[20+length:]
    header=data[:8]+struct.pack("<I",20+len(chunk)+len(rest))
    Path(path).write_bytes(header+struct.pack("<I",len(chunk))+b"JSON"+chunk+rest)


def pbr(name, color, metal=0, roughness=.50, alpha=1, emission=0):
    mat=bpy.data.materials.new(name)
    mat.use_nodes=True
    mat.diffuse_color=(*color,alpha)
    bsdf=mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value=(*color,1)
    bsdf.inputs["Metallic"].default_value=metal
    bsdf.inputs["Roughness"].default_value=roughness
    bsdf.inputs["Alpha"].default_value=alpha
    if emission:
        bsdf.inputs["Emission Color"].default_value=(*color,1)
        bsdf.inputs["Emission Strength"].default_value=emission
    return mat


def mesh(name,verts,faces,material):
    data=bpy.data.meshes.new(name)
    data.from_pydata(verts,[],faces)
    data.update()
    data.materials.append(material)
    obj=bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(obj)
    return obj


def cube(name,center,dimensions,material,bevel=0,rotation=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center)
    obj=bpy.context.object
    obj.name=name
    obj.dimensions=dimensions
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if rotation:
        obj.rotation_mode="QUATERNION"
        obj.rotation_quaternion=rotation
    obj.data.materials.append(material)
    if bevel:
        modifier=obj.modifiers.new("Soft forged edges","BEVEL")
        modifier.width=bevel
        modifier.segments=2
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def bar(name,a,b,width,depth,material,bevel):
    a,b=Vector(a),Vector(b)
    d=b-a
    return cube(name,(a+b)*.5,(width,depth,d.length),material,bevel,
                d.to_track_quat("Z","Y"))


def revolve(name,profile,sides,material,closed=False,smooth=False,at=(0,0,0)):
    vertices=[]
    for radius,z in profile:
        vertices.extend((at[0]+radius*cos(tau*i/sides),at[1]+radius*sin(tau*i/sides),at[2]+z)
                        for i in range(sides))
    faces=[]
    for i in range(len(profile) if closed else len(profile)-1):
        nxt=(i+1)%len(profile)
        for j in range(sides):
            k=(j+1)%sides
            faces.append((i*sides+j,i*sides+k,nxt*sides+k,nxt*sides+j))
    if not closed:
        faces.append(tuple(reversed(range(sides))))
        faces.append(tuple(range(len(vertices)-sides,len(vertices))))
    obj=mesh(name,vertices,faces,material)
    if smooth:
        for face in obj.data.polygons:
            face.use_smooth=True
    return obj


def link(name, center, heading, width, height, wire, material):
    center=Vector(center)
    across=Vector((cos(heading),sin(heading),0))
    perpendicular=Vector((-sin(heading),cos(heading),0))
    vertical=Vector((0,0,1))
    around,sides=20,6
    verts,faces=[],[]
    for i in range(around):
        angle=tau*i/around
        point=center+across*(width*cos(angle))+vertical*(height*sin(angle))
        normal=(across*(height*cos(angle))+vertical*(width*sin(angle))).normalized()
        for j in range(sides):
            bend=tau*j/sides
            verts.append(point+wire*(normal*cos(bend)+perpendicular*sin(bend)))
    for i in range(around):
        for j in range(sides):
            k=(j+1)%sides
            n=(i+1)%around
            faces.append((i*sides+j,n*sides+j,n*sides+k,i*sides+k))
    obj=mesh(name,verts,faces,material)
    for face in obj.data.polygons:
        face.use_smooth=True
    return obj


def join(name,objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.object.join()
    obj=bpy.context.view_layer.objects.active
    obj.name=obj.data.name=name
    return obj


def point_at(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()


def action_curves(obj):
    """Return the F-curves of the object's action in Blender 4.3 and in Blender 5."""
    animation=obj.animation_data
    slot=getattr(animation,"action_slot",None)
    if slot is not None:
        from bpy_extras.anim_utils import action_get_channelbag_for_slot
        channelbag=action_get_channelbag_for_slot(animation.action,slot)
        if channelbag is not None:
            return channelbag.fcurves
    return animation.action.fcurves


def animate(pivot):
    pivot.rotation_mode="QUATERNION"
    for step in range(25):
        phase=tau*step/24 if step<24 else 0
        qx=Quaternion((1,0,0),radians(13.5)*sin(phase))
        qy=Quaternion((0,1,0),radians(9.5)*sin(phase+.35))
        qz=Quaternion((0,0,1),radians(3.0)*sin(phase-.55))
        pivot.rotation_quaternion=qz@qy@qx
        pivot.keyframe_insert(data_path="rotation_quaternion",frame=step*4,group="Swing")
    action=pivot.animation_data.action
    action.name="Lantern Swing"
    for curve in action_curves(pivot):
        for key in curve.keyframe_points:
            key.interpolation="LINEAR"
        curve.modifiers.new(type="CYCLES")


def lantern():
    mount=bpy.data.objects.new("Lantern mount",None)
    bpy.context.collection.objects.link(mount)
    pivot=bpy.data.objects.new("Suspension pivot",None)
    bpy.context.collection.objects.link(pivot)
    pivot.parent=mount
    pivot.empty_display_type="SPHERE"
    pivot.empty_display_size=.025
    pivot["loop_seconds"]=PERIOD/FPS

    steel=pbr("Forged black iron",(.047,.048,.043),.89,.43)
    bronze=pbr("Heat-darkened bronze",(.22,.112,.046),.81,.36)
    panes=pbr("Old clear glass",(.79,.665,.49),0,.18,alpha=.115)
    flame=pbr("Amber flame",(.99,.217,.014),0,.39,emission=2.2)
    core=pbr("Warm flame core",(1,.63,.16),0,.39,emission=5.0)
    wick=pbr("Charred wick",(.025,.020,.016),0,.85)
    lamp_oil=pbr("Oil reservoir",(.18,.098,.036),.56,.42)

    socket=cube("Mounting plate",(0,0,.016),(.072,.061,.022),steel,.004)
    ring=link("Fixed mounting eye",(0,0,.005),.12,.016,.019,.0044,steel)
    fixed=join("Fixed mounting hardware",[socket,ring])
    fixed.parent=mount

    chain_parts=[link("Chain link",(0,0,-.022-.043*i),.12+tau*.25*(i%2),
                      .0127,.027,.0039,steel) for i in range(6)]
    chain_parts.append(link("Lantern eye",(0,0,-.273),.12+tau*.25,.0145,.0235,.0049,bronze))
    chain=join("Suspension chain",chain_parts)
    chain.parent=pivot

    # The roof starts at the upper rim and closes against a narrow vent cap.
    iron=[
        revolve("Lower casing",[(.104,-.706),(.131,-.691),(.141,-.665),(.133,-.639)],6,steel),
        revolve("Heel ring",[(.137,-.669),(.143,-.674),(.142,-.684),(.131,-.688)],6,steel,closed=True),
        revolve("Lower rail",[(.128,-.623),(.139,-.623),(.141,-.632),(.136,-.645),(.128,-.645)],6,steel,closed=True),
        revolve("Crown overhang",[(.164,-.404),(.172,-.410),(.165,-.419),(.149,-.420),
                                   (.147,-.410)],6,steel,closed=True),
        revolve("Sloped iron crown",[(.157,-.407),(.142,-.389),(.071,-.339),(.049,-.326),
                                     (.049,-.305),(.035,-.298)],6,steel),
        revolve("Vent cap",[(.053,-.326),(.059,-.322),(.056,-.311),(.046,-.304)],12,steel),
    ]
    brass=[
        revolve("Base bronze bead",[(.115,-.704),(.123,-.702),(.131,-.694),(.124,-.691)],6,bronze,closed=True),
        revolve("Crown bronze bead",[(.148,-.423),(.158,-.420),(.158,-.413),(.151,-.411)],6,bronze,closed=True),
    ]
    glass=[]
    for i in range(6):
        a,b=i*tau/6,(i+1)*tau/6
        low=[Vector((.129*cos(angle),.129*sin(angle),-.633)) for angle in (a,b)]
        high=[Vector((.152*cos(angle),.152*sin(angle),-.421)) for angle in (a,b)]
        iron.append(bar("Corner post",low[0],high[0],.013,.015,steel,.0023))
        for z,width in ((-.454,.0048),(-.605,.0042)):
            p=low[0].lerp(high[0],(z+.633)/.212)
            q=low[1].lerp(high[1],(z+.633)/.212)
            iron.append(bar("Pane rail",p,q,width,width,steel,.0008))
        inset=.067
        points=(low[0].lerp(low[1],inset),low[1].lerp(low[0],inset),
                high[1].lerp(high[0],inset),high[0].lerp(high[1],inset))
        points=[Vector((p.x*.975,p.y*.975,p.z)) for p in points]
        glass.append(mesh("Glass pane",points,[(0,1,2,3)],panes))
        brass.append(cube("Bronze rivet",high[0]+Vector((.003*cos(a),.003*sin(a),-.012)),
                          (.013,.013,.011),bronze,.0024))
        angle=(a+b)*.5
        recess=(.123*cos(angle),.123*sin(angle),-.677)
        brass.append(cube("Base fastener",recess,(.014,.010,.010),bronze,.0023,
                          Quaternion((0,0,1),angle)))

    for obj in (join("Wrought iron cage",iron),join("Bronze collar and rivets",brass),
                join("Six glass panes",glass)):
        obj.parent=pivot
    burner=revolve("Oil cup",[(.048,-.638),(.054,-.628),(.052,-.620),(.030,-.610),
                              (.019,-.600)],16,lamp_oil,smooth=True)
    burner.parent=pivot
    revolve("Black wick",[(.006,-.605),(.006,-.590)],8,wick).parent=pivot
    revolve("Amber flame",[(.005,-.591),(.010,-.583),(.010,-.569),(.006,-.555),
                           (.0011,-.543)],12,flame,smooth=True,at=(.002,-.001,0)).parent=pivot
    revolve("Bright flame core",[(.002,-.591),(.0045,-.581),(.0041,-.569),(.0008,-.557)],
            10,core,smooth=True,at=(0,-.001,-.005)).parent=pivot

    light=bpy.data.lights.new("Lantern point light","POINT")
    light.energy=16
    light.color=(1,.503,.232)
    light.shadow_soft_size=.018
    emitter=bpy.data.objects.new("Lantern point light",light)
    bpy.context.collection.objects.link(emitter)
    emitter.parent=pivot
    emitter.location=(.001,0,-.536)

    for obj in (fixed,*pivot.children):
        if obj.type != "MESH" or obj.name=="Six glass panes":
            continue
        geometry=bmesh.new()
        geometry.from_mesh(obj.data)
        bmesh.ops.recalc_face_normals(geometry,faces=list(geometry.faces))
        geometry.to_mesh(obj.data)
        geometry.free()

    animate(pivot)
    return mount,pivot


def preview():
    scene=bpy.context.scene
    stage=bpy.data.collections.new("Lighting test stage")
    scene.collection.children.link(stage)

    def put(obj):
        for collection in list(obj.users_collection):
            collection.objects.unlink(obj)
        stage.objects.link(obj)
        return obj

    wall=pbr("Test wall - blue-gray plaster",(.179,.203,.216),0,.89)
    nodes,links=wall.node_tree.nodes,wall.node_tree.links
    noise=nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value=104
    noise.inputs["Roughness"].default_value=.74
    bump=nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value=.35
    bump.inputs["Distance"].default_value=.009
    links.new(noise.outputs["Fac"],bump.inputs["Height"])
    links.new(bump.outputs["Normal"],nodes.get("Principled BSDF").inputs["Normal"])
    stage_object=put(cube("Test wall",(0,.262,-.37),(4,.05,4),wall))
    floor=pbr("Neutral test floor",(.12,.147,.155),0,.83)
    put(cube("Test floor",(0,0,-1.015),(4,4,.045),floor))
    dark=pbr("Dark oak mount",(.125,.074,.038),0,.72)
    put(cube("Support beam",(0,.085,.061),(.47,.40,.065),dark,.007))
    stage_object["preview_only"]=True

    scene.world=bpy.data.worlds.new("Dark lighting test world")
    scene.world.use_nodes=True
    background=scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value=(.063,.095,.145,1)
    background.inputs["Strength"].default_value=.19
    area=bpy.data.lights.new("Cool test fill","AREA")
    area.energy=6.5
    area.shape="DISK"
    area.size=.68
    area.color=(.60,.76,1)
    fill=bpy.data.objects.new("Cool test fill",area)
    stage.objects.link(fill)
    fill.location=(-.53,-.73,.13)
    point_at(fill,(0,0,-.42))

    data=bpy.data.cameras.new("Lantern close view")
    data.lens=53
    cam=bpy.data.objects.new("Lantern close view",data)
    stage.objects.link(cam)
    cam.location=(.65,-1.53,-.25)
    point_at(cam,(0,0,-.386))
    scene.camera=cam
    scene.render.engine="CYCLES"
    scene.cycles.samples=38
    scene.cycles.transparent_max_bounces=12
    scene.cycles.use_denoising=False
    scene.render.resolution_x,scene.render.resolution_y=850,960
    scene.render.image_settings.file_format="PNG"
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=="VIEW_3D":
                area.spaces.active.region_3d.view_perspective="CAMERA"
    return scene


def make_renders(scene,output):
    directory=output/"renders"
    directory.mkdir(parents=True,exist_ok=True)
    scene.frame_set(10)
    scene.render.filepath=str(directory/"lantern-lighting.png")
    bpy.ops.render.render(write_still=True)
    scene.render.resolution_x,scene.render.resolution_y=315,356
    scene.cycles.samples=8
    scene.cycles.seed=91
    scene.cycles.use_animated_seed=False
    with TemporaryDirectory(prefix="lantern-frames-") as temp:
        frames=[]
        for i in range(25):
            scene.frame_set(int(i*PERIOD/25))
            fn=str(Path(temp)/f"{i:02d}.png")
            frames.append(fn)
            scene.render.filepath=fn
            bpy.ops.render.render(write_still=True)
        subprocess.run(["magick","-delay","16",*frames,"-loop","0",
                        "+dither","-colors","96","-layers","Optimize",
                        str(directory/"lantern-swing.gif")],check=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path,default=ASSET)
    parser.add_argument("--no-renders",action="store_true")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    output=args.output_dir.resolve()
    output.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.unit_settings.system="METRIC"
    scene.render.fps=FPS
    scene.frame_start,scene.frame_end=0,PERIOD
    _,pivot=lantern()
    scene.frame_set(0)
    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active=pivot
    bpy.ops.export_scene.gltf(filepath=str(output/"hanging-lantern.glb"),export_format="GLB",
                              use_selection=True,export_animations=True,export_lights=True,
                              export_extras=True,export_animation_mode="ACTIONS")
    light_optional(output/"hanging-lantern.glb")
    scene=preview()
    scene.frame_set(10)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(output/"hanging-lantern.blend"),relative_remap=False)
    if not args.no_renders:
        make_renders(scene,output)


if __name__=="__main__":
    main()

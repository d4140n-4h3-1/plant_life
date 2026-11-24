bl_info = {"name":"Hydroxus Rivers and Streams","version":(0,2,0),"blender":(5,0,0),"category":"3D View"}
from bisect import bisect_left
from itertools import accumulate
import math
from random import Random

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
from mathutils.kdtree import KDTree
from bpy.props import BoolProperty, FloatProperty, IntProperty

def downhill(points, adjacency, start, limit):
    route=[start]
    for _ in range(limit):
        a=route[-1]
        candidates=[]
        for b in adjacency[a]:
            delta=points[b]-points[a]
            horizontal=math.hypot(delta.x,delta.y)
            if horizontal>1e-8 and delta.z < -1e-6:
                candidates.append((-delta.z/horizontal,b))
        if not candidates: break
        route.append(max(candidates)[1])
    return route

def set_water_uv(water):
    """Write downstream and cross-channel distances in meters to TEXCOORD_0."""
    mesh = water.data
    uv = mesh.uv_layers.get("FlowUV") or mesh.uv_layers.new(name="FlowUV")
    mesh.uv_layers.active = uv
    uv.active_render = True
    distance = 0.0
    previous = None
    coordinates = []
    for i in range(0, len(mesh.vertices), 2):
        left, right = mesh.vertices[i].co, mesh.vertices[i + 1].co
        center = (left + right) / 2
        if previous is not None:
            distance += (center - previous).length
        previous = center
        width = (right - left).length
        coordinates.extend(((distance, 0.0), (distance, width)))
    for loop in mesh.loops:
        uv.data[loop.index].uv = coordinates[loop.vertex_index]
    mesh.update()


def _water_triangles(waterways):
    triangles = []
    for water in waterways:
        mesh = water.data
        mesh.calc_loop_triangles()
        uv = mesh.uv_layers["FlowUV"]
        for triangle in mesh.loop_triangles:
            positions = [water.matrix_world @ mesh.vertices[i].co for i in triangle.vertices]
            coords = [Vector((*uv.data[i].uv, 0.0)) for i in triangle.loops]
            a, b, c = positions
            projected_area = abs((b - a).cross(c - a).z) * 0.5
            if projected_area > 1e-8:
                triangles.append((positions, coords, projected_area))
    return triangles


STONE_PALETTE = (
    (0.09, 0.075, 0.057), (0.17, 0.135, 0.096), (0.24, 0.21, 0.17),
    (0.105, 0.13, 0.105), (0.16, 0.135, 0.13), (0.29, 0.25, 0.19),
)


def _bed_material():
    name = "Hydroxus wet gravel"
    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name)
        material.use_nodes = True
        nodes = material.node_tree.nodes
        shader = nodes.get("Principled BSDF")
        shader.inputs["Roughness"].default_value = 0.73
        import numpy as np

        tile = 96
        atlas = np.ones((2 * tile, 3 * tile, 4), dtype=np.float32)
        rng = np.random.default_rng(1407)
        y, x = np.mgrid[0:tile, 0:tile] / tile
        for index, shade in enumerate(STONE_PALETTE):
            phase = rng.uniform(0, math.tau)
            broad = np.sin(15 * x + 8 * y + phase) * np.cos(10 * y - 18 * x)
            flecks = rng.normal(0, 0.12, size=x.shape)
            veins = np.maximum(0, np.cos(22 * x + 10 * y + 1.2 * np.sin(16 * y) + phase)) ** 13
            relief = (0.90 + 0.15 * broad + flecks + 0.11 * veins)
            row, col = divmod(index, 3)
            atlas[row*tile:(row+1)*tile, col*tile:(col+1)*tile, :3] = np.maximum(
                0.0, relief[..., None] * np.array(shade)
            )
        image = bpy.data.images.new("Hydroxus wet stone atlas", width=3 * tile, height=2 * tile)
        # The image stores sRGB values for portable glTF base-color sampling.
        rgb = atlas[..., :3]
        atlas[..., :3] = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * rgb ** (1 / 2.4) - 0.055)
        image.pixels.foreach_set(atlas.ravel())
        image.pack()
        texture = nodes.new("ShaderNodeTexImage")
        texture.image = image
        material.node_tree.links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    return material


def dress_channel_beds(terrain, waterways, seed, collection):
    """Shape and dress a terrain beneath one or more final FlowUV water surfaces."""
    bpy.context.view_layer.update()
    triangles = _water_triangles(waterways)
    if not triangles:
        return None
    water_tree = BVHTree.FromPolygons(
        [point for positions, _, _ in triangles for point in positions],
        [(i, i + 1, i + 2) for i in range(0, len(triangles) * 3, 3)], all_triangles=True,
    )
    rng = Random(seed)
    phase = rng.uniform(0, math.tau)
    transform = terrain.matrix_world
    inverse = transform.inverted_safe()
    vertical_ray = inverse.to_3x3() @ Vector((0, 0, -1))
    normal_to_world = inverse.to_3x3().transposed()
    origin_z = max(point.z for positions, _, _ in triangles for point in positions) + 1.0
    tint = terrain.data.color_attributes.get("Trail tint")

    def water_at(x, y):
        hit, _, triangle, _ = water_tree.ray_cast((x, y, origin_z), (0, 0, -1))
        return hit, triangle

    for vertex in terrain.data.vertices:
        point = transform @ vertex.co
        hit, triangle = water_at(point.x, point.y)
        if hit is None or hit.z - point.z < 0.035:
            continue
        positions, coords, _ = triangles[triangle]
        along, cross, _ = barycentric_transform(hit, *positions, *coords)
        depth = hit.z - point.z
        # Alternate low gravel bars and troughs along the current, eroding the deeper runs.
        bar = math.sin(along * 1.18 + 1.65 * cross + phase)
        scour = math.cos(along * 0.51 - 2.1 * cross + phase)
        texture = math.sin(along * 5.1 + cross * 8.6) * math.cos(cross * 6.7 - along * 2.2)
        envelope = min(1.0, max(0.0, (depth - 0.035) / 0.22))
        relief = (0.079 * bar + 0.062 * scour + 0.018 * texture) * envelope
        point.z = min(hit.z - 0.035, point.z + relief)
        vertex.co = inverse @ point
        if tint is not None:
            deposit = min(1.0, max(0.0, (0.43 - depth) * 2.7 + bar * 0.24))
            fines = (0.38, 0.34, 0.26)
            gravel = (0.83, 0.71, 0.54)
            shift = 0.91 + 0.11 * texture
            tint.data[vertex.index].color = (
                *((fine + (coarse - fine) * deposit) * shift for fine, coarse in zip(fines, gravel)),
                1.0,
            )
    terrain.data.update()
    bpy.context.view_layer.update()
    bed = BVHTree.FromObject(terrain, bpy.context.evaluated_depsgraph_get())

    # Stones share one surface, with compact caps embedded in the bed.
    vertices, faces, stone_uvs = [], [], []
    cumulative = list(accumulate(triangle[2] for triangle in triangles))
    target = min(480, max(1, round(cumulative[-1] * 9)))
    occupied = set()
    for _ in range(target * 5):
        if len(occupied) >= target:
            break
        positions, coords, _ = triangles[bisect_left(cumulative, rng.random() * cumulative[-1])]
        a, b, c = positions
        r, t = rng.random(), rng.random()
        if r + t > 1.0:
            r, t = 1.0 - r, 1.0 - t
        water_point = a + (b - a) * r + (c - a) * t
        uv = coords[0] + (coords[1] - coords[0]) * r + (coords[2] - coords[0]) * t
        cluster = 0.50 + 0.28 * math.sin(1.18 * uv.x + 1.65 * uv.y + phase)
        cluster += 0.21 * math.sin(3.7 * uv.x - 7.2 * uv.y)
        if rng.random() > cluster:
            continue
        origin = Vector((water_point.x, water_point.y, origin_z))
        ground, normal, _, _ = bed.ray_cast(inverse @ origin, vertical_ray)
        if ground is None or (normal_to_world @ normal).normalized().z < 0.62:
            continue
        ground = transform @ ground
        depth = water_point.z - ground.z
        if not 0.045 < depth < 0.70:
            continue
        cell = (math.floor(ground.x / 0.065), math.floor(ground.y / 0.065))
        if cell in occupied:
            continue
        occupied.add(cell)
        radius = 0.027 + 0.138 * rng.random() ** 2.2
        height = min(depth * 0.56, radius * rng.uniform(0.35, 0.83))
        length = radius * rng.uniform(1.0, 1.55)
        # Solve the UV basis for the direction of increasing U on this triangle.
        dv1, dv2 = coords[1].y - coords[0].y, coords[2].y - coords[0].y
        flow = (b - a) * dv2 - (c - a) * dv1
        angle = math.atan2(flow.y, flow.x) + rng.uniform(-0.95, 0.95)
        axis = Vector((math.cos(angle), math.sin(angle), 0))
        lateral = Vector((-axis.y, axis.x, 0))
        start = len(vertices)
        row, col = divmod(rng.randrange(len(STONE_PALETTE)), 3)
        sides = 7
        for i in range(sides):
            theta = math.tau * i / sides + rng.uniform(-0.15, 0.15)
            radial = axis * (math.cos(theta) * length) + lateral * (math.sin(theta) * radius)
            radial *= rng.uniform(0.82, 1.16)
            vertices.extend((ground + radial - Vector((0, 0, height * 0.26)),
                             ground + radial * 0.74 + Vector((0, 0, height * rng.uniform(0.54, 0.83)))))
            u = radial.dot(axis) / length * 0.34
            v = radial.dot(lateral) / radius * 0.34
            stone_uvs.extend((((col + 0.5 + u) / 3, (row + 0.5 + v) / 2),
                              ((col + 0.5 + 0.74*u) / 3, (row + 0.5 + 0.74*v) / 2)))
        vertices.append(ground + axis * rng.uniform(-length * 0.2, length * 0.2)
                        + Vector((0, 0, height)))
        stone_uvs.append(((col + 0.5) / 3, (row + 0.5) / 2))
        for i in range(sides):
            base = start + i * 2
            next_base = start + (i + 1) % sides * 2
            faces.extend(((base, next_base, next_base + 1, base + 1),
                          (base + 1, next_base + 1, start + sides * 2)))
    if not faces:
        return None

    gravel = bpy.data.meshes.new("Embedded channel gravel")
    gravel.from_pydata(vertices, [], faces)
    gravel.update()
    gravel.materials.append(_bed_material())
    uv = gravel.uv_layers.new(name="Stone atlas")
    for loop in gravel.loops:
        uv.data[loop.index].uv = stone_uvs[loop.vertex_index]
    for face in gravel.polygons:
        face.use_smooth = True
    obj = bpy.data.objects.new(gravel.name, gravel)
    obj["stone_count"] = len(occupied)
    obj["bed_seed"] = str(seed)
    collection.objects.link(obj)
    return obj


class HX_OT_river(bpy.types.Operator):
    bl_idname="hx.river"; bl_label="Trace River and Bed from 3D Cursor"; bl_options={'REGISTER','UNDO'}
    build_bed: BoolProperty(default=True, options={'HIDDEN'})

    @classmethod
    def poll(cls,c):
        return c.object and c.object.type=='MESH' and c.mode=='OBJECT'
    def execute(self,c):
        obj=c.object; mesh=obj.data; s=c.scene
        if mesh.users>1:
            self.report({'ERROR'},'Make terrain mesh single-user first'); return {'CANCELLED'}
        matrix=obj.matrix_world; inv=matrix.inverted()
        points=[matrix@v.co for v in mesh.vertices]
        if not points: return {'CANCELLED'}
        adj=[set() for p in points]
        for e in mesh.edges:
            a,b=e.vertices; adj[a].add(b); adj[b].add(a)
        cursor=c.scene.cursor.location
        start=min(range(len(points)),key=lambda i:(points[i].x-cursor.x)**2+(points[i].y-cursor.y)**2)
        route=downhill(points,adj,start,s.hxr_steps)
        if len(route)<2:
            self.report({'WARNING'},'Source is in a depression or on flat terrain'); return {'CANCELLED'}
        path=[points[i].copy() for i in route]
        width=s.hxr_width; depth=s.hxr_depth
        tree=KDTree(len(points))
        for i,p in enumerate(points): tree.insert(Vector((p.x,p.y,0)),i)
        tree.balance()
        cuts={}
        for a,b in zip(path,path[1:]):
            delta=b-a; length=math.hypot(delta.x,delta.y)
            if length<1e-8: continue
            mid=(a+b)*.5
            for _,i,_ in tree.find_range(Vector((mid.x,mid.y,0)),length*.5+width):
                p=points[i]
                t=max(0,min(1,((p.x-a.x)*delta.x+(p.y-a.y)*delta.y)/(length*length)))
                q=a+delta*t; d=math.hypot(p.x-q.x,p.y-q.y)
                if d>=width: continue
                profile=(1-(d/width)**2)**2
                target=q.z-depth*profile
                cuts[i]=min(cuts.get(i,p.z),p.z,target)
        for i,z in cuts.items():
            p=points[i].copy(); p.z=z; mesh.vertices[i].co=inv@p
        mesh.update()
        verts=[]; faces=[]
        for i,p in enumerate(path):
            tangent=path[min(i+1,len(path)-1)]-path[max(i-1,0)]
            lateral=Vector((-tangent.y,tangent.x,0))
            if lateral.length<1e-8: lateral=Vector((1,0,0))
            lateral.normalize()
            center=p.copy(); center.z-=depth*.55
            verts.extend([center-lateral*width*.48,center+lateral*width*.48])
            if i: faces.append((2*i-2,2*i,2*i+1,2*i-1))
        water=bpy.data.meshes.new('River Surface'); water.from_pydata(verts,[],faces); water.update()
        river=bpy.data.objects.new('Hydroxus River',water); c.collection.objects.link(river)
        mat=bpy.data.materials.get('Hydroxus Water') or bpy.data.materials.new('Hydroxus Water')
        mat.use_nodes=True; bs=mat.node_tree.nodes.get('Principled BSDF')
        if bs:
            bs.inputs['Base Color'].default_value=(.025,.13,.15,1)
            bs.inputs['Roughness'].default_value=.12
            bs.inputs['Transmission Weight'].default_value=.85
            bs.inputs['IOR'].default_value=1.333
        water.materials.append(mat)
        flow=water.attributes.new('flow_direction','FLOAT_VECTOR','POINT')
        for i in range(len(path)):
            direction=path[min(i+1,len(path)-1)]-path[max(i-1,0)]
            direction.normalize()
            for j in (2*i,2*i+1): flow.data[j].vector=direction
        set_water_uv(river)
        if self.build_bed:
            dress_channel_beds(obj, (river,), s.hxr_bed_seed, c.collection)
        river['source_terrain']=obj.name
        river['termination']='step_limit' if len(route)==s.hxr_steps+1 else 'local_minimum_or_boundary'
        self.report({'INFO'},f'Created downhill channel with {len(route)} samples; check banks and endpoint')
        return {'FINISHED'}

class HX_PT_river(bpy.types.Panel):
    bl_label='Rivers and Streams'; bl_idname='HX_PT_river'; bl_space_type='VIEW_3D'; bl_region_type='UI'; bl_category='Terrain'
    def draw(self,c):
        l=self.layout; s=c.scene
        l.label(text='Place 3D cursor at water source')
        l.prop(s,'hxr_width'); l.prop(s,'hxr_depth'); l.prop(s,'hxr_steps')
        l.prop(s,'hxr_bed_seed')
        l.operator('hx.river')

def register():
    bpy.utils.register_class(HX_OT_river); bpy.utils.register_class(HX_PT_river)
    bpy.types.Scene.hxr_width=FloatProperty(name='Channel Half Width (m)',default=2,min=.05,max=1000)
    bpy.types.Scene.hxr_depth=FloatProperty(name='Channel Depth (m)',default=.6,min=.01,max=100)
    bpy.types.Scene.hxr_bed_seed=IntProperty(name='Bed Seed',default=2741,min=0)
    bpy.types.Scene.hxr_steps=IntProperty(name='Maximum Flow Steps',default=2000,min=1,max=100000)
def unregister():
    for k in ('hxr_width','hxr_depth','hxr_steps','hxr_bed_seed'): delattr(bpy.types.Scene,k)
    bpy.utils.unregister_class(HX_PT_river); bpy.utils.unregister_class(HX_OT_river)
if __name__=='__main__': register()

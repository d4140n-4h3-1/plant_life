bl_info = {"name":"Hydroxus Rivers and Streams","version":(0,1,0),"blender":(5,0,0),"category":"3D View"}
import bpy, math
from mathutils import Vector
from mathutils.kdtree import KDTree
from bpy.props import FloatProperty, IntProperty, EnumProperty

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


class HX_OT_river(bpy.types.Operator):
    bl_idname="hx.river"; bl_label="Trace River from 3D Cursor"; bl_options={'REGISTER','UNDO'}
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
            if i: faces.append((2*i-2,2*i-1,2*i+1,2*i))
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
        l.operator('hx.river')

def register():
    bpy.utils.register_class(HX_OT_river); bpy.utils.register_class(HX_PT_river)
    bpy.types.Scene.hxr_width=FloatProperty(name='Channel Half Width (m)',default=2,min=.05,max=1000)
    bpy.types.Scene.hxr_depth=FloatProperty(name='Channel Depth (m)',default=.6,min=.01,max=100)
    bpy.types.Scene.hxr_steps=IntProperty(name='Maximum Flow Steps',default=2000,min=1,max=100000)
def unregister():
    for k in ('hxr_width','hxr_depth','hxr_steps'): delattr(bpy.types.Scene,k)
    bpy.utils.unregister_class(HX_PT_river); bpy.utils.unregister_class(HX_OT_river)
if __name__=='__main__': register()

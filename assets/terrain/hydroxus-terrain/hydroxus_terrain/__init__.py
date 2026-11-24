bl_info = {'name':'Hydroxus Terrain Brushes','author':'Hydroxus','version':(0,1,0),'blender':(5,0,0),'location':'View3D > Sidebar > Terrain','category':'3D View'}
import bpy, math, random
from mathutils import Vector, noise
from bpy_extras import view3d_utils
from bpy.props import EnumProperty, FloatProperty, IntProperty
SOILS = {
'Loam':((.045,.025,.012),(.19,.105,.047),.88,65,.12),
'Clay':((.12,.045,.023),(.36,.16,.075),.82,90,.08),
'Sand':((.27,.17,.08),(.65,.48,.25),.9,150,.07),
'Silt':((.09,.075,.05),(.29,.24,.16),.87,110,.06),
'Peat':((.018,.012,.008),(.095,.055,.025),.92,45,.15),
'Gravel':((.07,.065,.055),(.38,.34,.27),.9,18,.28),
'Chalk':((.26,.24,.19),(.72,.69,.58),.9,55,.12),
'Mud':((.035,.022,.013),(.14,.09,.045),.34,35,.06)}

def material():
    name='Hydroxus | Soil Layers'
    m=bpy.data.materials.get(name)
    if m: return m
    m=bpy.data.materials.new(name); m.use_nodes=True
    n=m.node_tree.nodes; l=m.node_tree.links; n.clear()
    out=n.new('ShaderNodeOutputMaterial'); out.location=(1000,0)
    tex=n.new('ShaderNodeTexCoord'); tex.location=(-1100,0)
    previous=None
    for i,(soil,(dark,light,rough,scale,bump)) in enumerate(SOILS.items()):
        y=-i*420
        t=n.new('ShaderNodeTexNoise'); t.location=(-850,y); t.inputs['Scale'].default_value=scale; t.inputs['Detail'].default_value=3
        l.new(tex.outputs['Object'],t.inputs['Vector'])
        r=n.new('ShaderNodeValToRGB'); r.location=(-600,y); r.color_ramp.elements[0].color=(*dark,1); r.color_ramp.elements[1].color=(*light,1); l.new(t.outputs['Fac'],r.inputs[0])
        b=n.new('ShaderNodeBump'); b.location=(-350,y-170); b.inputs['Strength'].default_value=bump; b.inputs['Distance'].default_value=.025; l.new(t.outputs['Fac'],b.inputs['Height'])
        p=n.new('ShaderNodeBsdfPrincipled'); p.location=(-100,y); p.inputs['Roughness'].default_value=rough; l.new(r.outputs['Color'],p.inputs['Base Color']); l.new(b.outputs['Normal'],p.inputs['Normal'])
        if previous is None: previous=p.outputs[0]; continue
        a=n.new('ShaderNodeAttribute'); a.attribute_name='hx_'+soil; a.location=(200,y-120)
        mix=n.new('ShaderNodeMixShader'); mix.location=(500,y); l.new(a.outputs['Fac'],mix.inputs[0]); l.new(previous,mix.inputs[1]); l.new(p.outputs[0],mix.inputs[2]); previous=mix.outputs[0]
    l.new(previous,out.inputs['Surface']); return m

def prepare(obj):
    mesh=obj.data
    for soil in list(SOILS)[1:]:
        name='hx_'+soil
        if mesh.attributes.get(name) is None: mesh.attributes.new(name,'FLOAT','POINT')
    m=material()
    if m.name not in obj.data.materials: obj.data.materials.append(m)
    idx=list(obj.data.materials).index(m)
    for p in mesh.polygons: p.material_index=idx

class HX_OT_generate(bpy.types.Operator):
    bl_idname='hx.generate'; bl_label='Generate Terrain'; bl_options={'REGISTER','UNDO'}
    def execute(self,c):
        s=c.scene; count=s.hx_resolution; size=s.hx_size; rng=random.Random(s.hx_seed); off=rng.uniform(-1000,1000)
        verts=[]; faces=[]
        for j in range(count):
            for i in range(count):
                x=size*(i/(count-1)-.5); y=size*(j/(count-1)-.5)
                z=s.hx_height*noise.fractal(Vector((x/size*4+off,y/size*4,0)),1.0,2.0,4)
                verts.append((x,y,z))
        for j in range(count-1):
            for i in range(count-1):
                a=j*count+i; faces.append((a,a+1,a+count+1,a+count))
        mesh=bpy.data.meshes.new('Hydroxus Terrain'); mesh.from_pydata(verts,[],faces); mesh.update()
        obj=bpy.data.objects.new('Hydroxus Terrain',mesh); c.collection.objects.link(obj)
        for o in c.selected_objects: o.select_set(False)
        obj.select_set(True); c.view_layer.objects.active=obj; prepare(obj)
        for p in mesh.polygons: p.use_smooth=True
        return {'FINISHED'}

class HX_OT_brush(bpy.types.Operator):
    bl_idname='hx.brush'; bl_label='Apply Interactive Brush'; bl_options={'REGISTER','UNDO','BLOCKING'}
    @classmethod
    def poll(cls,c): return c.object and c.object.type=='MESH' and c.mode=='OBJECT' and c.area.type=='VIEW_3D'
    def invoke(self,c,e):
        self.obj=c.object; self.region=next(r for r in c.area.regions if r.type=='WINDOW'); self.rv=c.space_data.region_3d; self.area=c.area; self.down=False; self.last=None
        self.coords=[v.co.copy() for v in self.obj.data.vertices]; self.old_indices=[p.material_index for p in self.obj.data.polygons]; self.old_slots=len(self.obj.data.materials); self.old_attrs={a.name:[d.value for d in a.data] for a in self.obj.data.attributes if a.name.startswith('hx_') and a.data_type=='FLOAT' and a.domain=='POINT'}
        self.adj=[[] for v in self.obj.data.vertices]
        for edge in self.obj.data.edges:
            a,b=edge.vertices; self.adj[a].append(b); self.adj[b].append(a)
        if c.scene.hx_mode=='PAINT': prepare(self.obj)
        c.window_manager.modal_handler_add(self); self.area.header_text_set('Hydroxus: drag LMB | Enter finish | Esc cancel'); return {'RUNNING_MODAL'}
    def dab(self,c,e):
        s=c.scene; obj=self.obj; mesh=obj.data; xy=(e.mouse_x-self.region.x,e.mouse_y-self.region.y)
        if not (0<=xy[0]<self.region.width and 0<=xy[1]<self.region.height): return
        origin=view3d_utils.region_2d_to_origin_3d(self.region,self.rv,xy); direction=view3d_utils.region_2d_to_vector_3d(self.region,self.rv,xy)
        inv=obj.matrix_world.inverted(); hit,pos,normal,index=obj.ray_cast(inv@origin,(inv.to_3x3()@direction).normalized())
        if not hit: return
        center=obj.matrix_world@pos; radius=s.hx_radius
        if self.last is not None and (center-self.last).length<radius*.12: return
        self.last=center; mode=s.hx_mode; old=[v.co.z for v in mesh.vertices] if mode=='SMOOTH' else None
        attrs={k:mesh.attributes['hx_'+k] for k in list(SOILS)[1:]} if mode=='PAINT' else {}
        for v in mesh.vertices:
            d=((obj.matrix_world@v.co)-center).length
            if d>=radius: continue
            w=(1-(d/radius)**2)**2*s.hx_strength
            if mode=='PAINT':
                for k,a in attrs.items():
                    val=a.data[v.index].value; a.data[v.index].value=val+(float(k==s.hx_soil)-val)*min(w,1)
            elif mode=='SMOOTH':
                neighbors=self.adj[v.index]
                if neighbors: v.co.z+=(sum(old[i] for i in neighbors)/len(neighbors)-old[v.index])*min(w,1)
            elif mode=='FLATTEN': v.co.z+=(pos.z-v.co.z)*min(w,1)
            elif mode=='ROUGHEN': v.co.z+=w*radius*.12*noise.noise_vector(v.co*3)[0]
            else: v.co.z+=w*radius*.12*(1 if mode=='RAISE' else -1)
        mesh.update(); self.area.tag_redraw()
    def modal(self,c,e):
        if e.type=='ESC':
            mesh=self.obj.data
            for v,co in zip(mesh.vertices,self.coords): v.co=co
            for a in list(mesh.attributes):
                if a.name.startswith('hx_') and a.name not in self.old_attrs: mesh.attributes.remove(a)
            for name,values in self.old_attrs.items():
                for d,val in zip(mesh.attributes[name].data,values): d.value=val
            while len(mesh.materials)>self.old_slots: mesh.materials.pop(index=len(mesh.materials)-1)
            for p,i in zip(mesh.polygons,self.old_indices): p.material_index=i
            mesh.update(); self.area.header_text_set(None); return {'CANCELLED'}
        if e.type in {'RET','NUMPAD_ENTER'}: self.area.header_text_set(None); return {'FINISHED'}
        if e.type=='LEFTMOUSE':
            self.down=e.value=='PRESS'; self.last=None
            if self.down: self.dab(c,e)
            return {'RUNNING_MODAL'}
        if e.type=='MOUSEMOVE' and self.down: self.dab(c,e); return {'RUNNING_MODAL'}
        return {'PASS_THROUGH'}

class HX_PT_panel(bpy.types.Panel):
    bl_label='Hydroxus Terrain'; bl_idname='HX_PT_terrain'; bl_space_type='VIEW_3D'; bl_region_type='UI'; bl_category='Terrain'
    def draw(self,c):
        l=self.layout; s=c.scene; box=l.box(); box.label(text='Generate Terrain')
        for p in ('hx_size','hx_resolution','hx_height','hx_seed'): box.prop(s,p)
        box.operator('hx.generate'); box=l.box(); box.label(text='Edit Selected Mesh')
        for p in ('hx_mode','hx_radius','hx_strength'): box.prop(s,p)
        if s.hx_mode=='PAINT': box.prop(s,'hx_soil')
        box.operator('hx.brush'); box.label(text='Enter: finish | Esc: cancel')

classes=(HX_OT_generate,HX_OT_brush,HX_PT_panel)
props={'hx_size':FloatProperty(name='Size',default=50,min=1,max=10000),'hx_resolution':IntProperty(name='Vertices per Side',default=129,min=3,max=513),'hx_height':FloatProperty(name='Relief',default=4,min=0,max=1000),'hx_seed':IntProperty(name='Seed',default=42),'hx_radius':FloatProperty(name='Radius',default=3,min=.01,max=1000),'hx_strength':FloatProperty(name='Strength',default=.4,min=.01,max=1),'hx_mode':EnumProperty(name='Brush',items=[(x,x.title(),'') for x in ('RAISE','LOWER','SMOOTH','FLATTEN','ROUGHEN','PAINT')]),'hx_soil':EnumProperty(name='Soil',items=[(x,x,'') for x in SOILS])}
def register():
    for cls in classes: bpy.utils.register_class(cls)
    for k,v in props.items(): setattr(bpy.types.Scene,k,v)
def unregister():
    for k in props: delattr(bpy.types.Scene,k)
    for cls in reversed(classes): bpy.utils.unregister_class(cls)
if __name__=='__main__': register()

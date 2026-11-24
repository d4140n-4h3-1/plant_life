use fyrox::{
    asset::untyped::ResourceKind,
    core::uuid::Uuid,
    material::{
        shader::{Shader, ShaderError, ShaderResource},
        Material, MaterialResource,
    },
    scene::mesh::{Mesh, RenderPath},
};

pub enum WaterBackend {
    OpenGl,
    Wgpu,
}

pub struct FlowingWater {
    material: MaterialResource,
    phase: f32,
    cycles_per_second: f32,
}

impl FlowingWater {
    pub fn attach(
        mesh: &mut Mesh,
        backend: WaterBackend,
        cycles_per_second: f32,
    ) -> Result<Self, ShaderError> {
        let source = match backend {
            WaterBackend::OpenGl => include_str!("water-opengl.shader"),
            WaterBackend::Wgpu => include_str!("water-wgpu.shader"),
        };
        let shader = ShaderResource::new_ok(
            Uuid::new_v4(),
            ResourceKind::Embedded,
            Shader::from_string(source)?,
        );
        let material = MaterialResource::new_ok(
            Uuid::new_v4(),
            ResourceKind::Embedded,
            Material::from_shader(shader),
        );

        mesh.set_render_path(RenderPath::Forward);
        mesh.set_cast_shadows(false);
        for surface in mesh.surfaces_mut() {
            surface.set_material(material.clone());
        }
        Ok(Self { material, phase: 0.0, cycles_per_second })
    }

    pub fn update(&mut self, delta_seconds: f32) {
        self.phase = (self.phase + delta_seconds * self.cycles_per_second).rem_euclid(1.0);
        self.material.data_ref().set_property("flowPhase", self.phase);
    }
}

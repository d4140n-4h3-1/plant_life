use fyrox::{
    asset::untyped::ResourceKind,
    core::{algebra::{Vector3, Vector4}, uuid::Uuid},
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
        Ok(Self {
            material,
            phase: 0.0,
            cycles_per_second,
        })
    }

    /// World-space direction from the water toward the sun.
    pub fn set_sun_direction(&self, direction: Vector3<f32>) {
        if let Some(direction) = direction.try_normalize(1.0e-6) {
            self.material.data_ref().set_property("sunDirection", direction);
        }
    }

    /// Each entry is a world-space center (xyz) and blending radius in meters (w).
    /// Give both connected meshes the same entry. Up to eight entries are supported.
    pub fn set_confluences(&self, junctions: &[Vector4<f32>]) {
        let junctions = junctions.iter().take(8).copied().collect::<Vec<_>>();
        self.material.data_ref().set_property("confluences", junctions);
    }

    /// Pass the same simulation clock to all connected water materials.
    pub fn set_confluence_time(&self, elapsed_seconds: f32) {
        let phase = (elapsed_seconds * 0.28).rem_euclid(1.0);
        self.material.data_ref().set_property("confluencePhase", phase);
    }

    pub fn update(&mut self, delta_seconds: f32) {
        self.phase = (self.phase + delta_seconds * self.cycles_per_second).rem_euclid(1.0);
        self.material.data_ref().set_property("flowPhase", self.phase);
    }
}

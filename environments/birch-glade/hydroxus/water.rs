use fyrox::{
    asset::untyped::ResourceKind,
    core::{
        algebra::{Vector3, Vector4},
        math::{aabb::AxisAlignedBoundingBox, octree::Octree, ray::Ray},
        uuid::Uuid,
    },
    material::{
        shader::{Shader, ShaderError, ShaderResource},
        Material, MaterialResource,
    },
    scene::mesh::{
        buffer::{VertexAttributeUsage, VertexReadTrait},
        Mesh, RenderPath,
    },
};

pub enum WaterBackend {
    OpenGl,
    Wgpu,
}

const MAX_OBSTACLE_RIPPLES: usize = 8;

pub struct FlowingWater {
    material: MaterialResource,
    phase: f32,
    obstacle_phase: f32,
    triangles: Vec<[Vector3<f32>; 3]>,
    contact_index: Option<Octree>,
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
        let mut water_material = Material::from_shader(shader);
        water_material.set_property("sceneColorWeight", 0.0_f32);
        water_material.set_property("reflectionWeight", 0.0_f32);
        let current = ((cycles_per_second.abs() - 0.06) / 0.34).clamp(0.0, 1.0)
            * cycles_per_second.signum();
        water_material.set_property("obstacleCurrent", current);
        water_material.set_property("bankRippleStrength", current.abs());
        let material = MaterialResource::new_ok(
            Uuid::new_v4(),
            ResourceKind::Embedded,
            water_material,
        );

        let mut triangles = Vec::new();
        for surface in mesh.surfaces() {
            let resource = surface.data_ref().data_ref();
            if let Some(data) = resource.as_loaded_ref() {
                for triangle in data.geometry_buffer.triangles_ref() {
                    let position = |index: u32| {
                        data.vertex_buffer
                            .get(index as usize)?
                            .read_3_f32(VertexAttributeUsage::Position)
                            .ok()
                    };
                    let [a, b, c] = triangle.0;
                    if let (Some(a), Some(b), Some(c)) = (position(a), position(b), position(c)) {
                        if (b - a).cross(&(c - a)).norm_squared() > 1.0e-12 {
                            triangles.push([a, b, c]);
                        }
                    }
                }
            }
        }
        let contact_index = (!triangles.is_empty()).then(|| Octree::new(&triangles, 24));

        mesh.set_render_path(RenderPath::Forward);
        mesh.set_cast_shadows(false);
        for surface in mesh.surfaces_mut() {
            surface.set_material(material.clone());
        }
        Ok(Self {
            material,
            phase: 0.0,
            obstacle_phase: 0.0,
            triangles,
            contact_index,
            cycles_per_second,
        })
    }

    /// Set ripple amplitude and foam for quiet ponds or slow spring pools.
    pub fn set_surface_activity(&self, waves: f32, foam: f32) {
        let mut material = self.material.data_ref();
        material.set_property("waveStrength", waves.clamp(0.0, 1.0));
        material.set_property("foamStrength", foam.clamp(0.0, 1.0));
    }

    /// Set the refracted contribution from zero to one.
    /// Requires the Hydroxus forward scene-color patch.
    pub fn set_refraction_strength(&self, strength: f32) {
        self.material
            .data_ref()
            .set_property("sceneColorWeight", strength.clamp(0.0, 1.0));
    }

    /// Enable short-range reflections of visible opaque scenery with the scene-color patch.
    pub fn set_reflection_strength(&self, strength: f32) {
        self.material
            .data_ref()
            .set_property("reflectionWeight", strength.clamp(0.0, 1.0));
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

    /// Override the ripple deformation along FlowUV's U axis. Zero is still water.
    pub fn set_obstacle_current(&self, current: f32) {
        self.material
            .data_ref()
            .set_property("obstacleCurrent", current.clamp(-1.0, 1.0));
    }

    /// Refresh contact ripples using world-space obstacle or collider bounds.
    /// Pass the current water mesh transform by supplying the same mesh used by attach.
    pub fn update_obstacles(
        &self,
        mesh: &Mesh,
        bounds: &[AxisAlignedBoundingBox],
        eye: Vector3<f32>,
    ) {
        let mut contacts: Vec<(f32, Vector4<f32>)> = Vec::with_capacity(MAX_OBSTACLE_RIPPLES);
        if let (Some(index), Some(inverse)) =
            (&self.contact_index, mesh.global_transform().try_inverse())
        {
            let mut candidates = Vec::new();
            for object in bounds {
                let half = (object.max - object.min) * 0.5;
                let center = object.min + half;
                if !center.iter().chain(half.iter()).all(|v| v.is_finite())
                    || half.x <= 0.0
                    || half.z <= 0.0
                    || half.y <= 0.012
                {
                    continue;
                }
                let distance = (center - eye).norm_squared();
                if contacts.len() == MAX_OBSTACLE_RIPPLES
                    && distance >= contacts[MAX_OBSTACLE_RIPPLES - 1].0
                {
                    continue;
                }
                let probes = [(0.0, 0.0), (-0.72, 0.0), (0.72, 0.0), (0.0, -0.72), (0.0, 0.72)];
                let wet = probes.into_iter()
                    .any(|(x, z)| {
                        let x = center.x + x * half.x;
                        let z = center.z + z * half.z;
                        let ray = Ray::from_two_points(
                            Vector3::new(x, object.max.y - 0.012, z),
                            Vector3::new(x, object.min.y + 0.012, z),
                        )
                        .transform(inverse);
                        index.ray_query(&ray, &mut candidates);
                        candidates.iter().any(|i| {
                            ray.triangle_intersection(&self.triangles[*i as usize]).is_some()
                        })
                    });
                if wet {
                    let at = contacts.partition_point(|entry: &(f32, Vector4<f32>)| entry.0 <= distance);
                    if contacts.len() == MAX_OBSTACLE_RIPPLES {
                        contacts.pop();
                    }
                    let ripple = Vector4::new(center.x, center.z, half.x.max(0.035), half.z.max(0.035));
                    contacts.insert(at, (distance, ripple));
                }
            }
        }
        let ripples: Vec<_> = contacts.into_iter().map(|(_, ripple)| ripple).collect();
        let mut material = self.material.data_ref();
        material.set_property("obstacleCount", ripples.len() as i32);
        material.set_property("obstacles", ripples);
    }

    pub fn update(&mut self, delta_seconds: f32) {
        self.phase = (self.phase + delta_seconds * self.cycles_per_second).rem_euclid(1.0);
        self.obstacle_phase = (self.obstacle_phase + delta_seconds * 1.15).rem_euclid(1.0);
        let mut material = self.material.data_ref();
        material.set_property("flowPhase", self.phase);
        material.set_property("obstaclePhase", self.obstacle_phase);
    }
}

# Birch Glade water for Hydroxus

Import [birch-glade.glb](../birch-glade.glb) and instantiate it in the game scene.
The mesh nodes named **Birch River** and **Fern Stream** each have a first UV set
in meters. U increases downstream and V spans the channel. The water shader uses
these distances to move its ripple patterns along the bends.

Copy `water.rs` and both `.shader` files into the same directory in the game's
Rust source and declare `mod water;`. The sample uses the fork's `fyrox` crate
name. After instantiating the GLB, pass each water mesh to `FlowingWater::attach`.
Choose `WaterBackend::Wgpu` or `WaterBackend::OpenGl` to match the engine build.

```rust
let river = FlowingWater::attach(river_mesh, WaterBackend::Wgpu, 0.23)?;
let stream = FlowingWater::attach(stream_mesh, WaterBackend::Wgpu, 0.38)?;
```

Keep both returned controllers in game state and call `update(context.dt)` on
each during the game update. The last argument sets the ripple phase cycles per
second. The shader samples the opaque scene depth to keep the water clear over
shallow gravel and increase absorption in deeper sections. Layered ripples tilt
the reflected sky and highlight, with broken foam in narrow bands where the
water meets banks and submerged rocks. The reflection is a procedural sky
gradient. The water mesh stays fixed.

For a day/night cycle, call `set_sun_direction` with the world-space vector from
the water toward the sun. Supply the directional light's world-space +Y axis
when using Wilderness's convention. The material expects opaque terrain and rocks
to write depth before the forward water pass, and uses perspective camera depth.

## Joining water surfaces

Birch Glade's tributary mesh is trimmed to the receiving bank and eased into
the river's surface height. The two meshes meet without overlapping translucent
faces. In the game, register the same world-space junction on both controllers
so the ripples and foam transition to one shared pattern at the seam.

```rust
use fyrox::core::algebra::Vector4;

// Birch Glade at its original import transform. xyz is the center, w the radius.
let junction = Vector4::new(-6.540, 0.805, -5.314, 2.2);
river.set_confluences(&[junction]);
stream.set_confluences(&[junction]);
```

Each update, call `set_confluence_time(context.elapsed_time)` on both controllers,
in addition to their regular `update(context.dt)` calls. If you move the imported
scene, transform the junction center with it. A receiving water surface can use
up to eight junctions.

To author another channel, use the
[Hydroxus Rivers and Streams add-on](../../../assets/terrain/hydroxus-terrain/hydroxus_rivers.py).
Its river operator writes flow UVs automatically. After editing a paired ribbon,
call `hydroxus_rivers.set_water_uv(water_object)` before joining or exporting.

At a junction, call the [water join tool](../../../assets/terrain/hydroxus-terrain/hydroxus_water_join.py)
as `join_water_channels(tributary, receiving)` after positioning the two meshes.
The tributary should end inside the receiver. The tool trims that overlap,
preserves the UVs, and returns the junction center in Blender world space. It
also stores a Blender-local center on the tributary in `join_center_local`.
Convert Blender coordinates `(x, y, z)` to glTF/Hydroxus coordinates
`(x, z, -y)` before using them in the game. Export with UVs enabled and
**FlowUV** as the first UV layer.

## Shoreline variants

The reference scene uses shoreline seed `2741`. Rebuild with any integer
`--shore-seed`, or use `--random-shore` to draw a fresh seed and print it in the
build log. The seed varies both banks independently, changes the shallow bank
profile, and breaks gravel and bank plants into uneven patches.

```sh
blender -b --python-exit-code 1 \
  --python environments/birch-glade/tools/build_birch_glade.py \
  -- --shore-seed 591038123 --output-dir /tmp/birch-glade-variant
```

Use the variant's `join_center_local` when setting its shader confluence.
The seed is recorded in each water node's GLB extras as `shore_seed`.

The forward renderer and scene-depth binding were checked against Wilderness's
pinned Hydroxus Vulkan revision, `63b5452`. Both shader stages were compiled
offscreen. An offscreen Vulkan draw verified that opacity increases with depth.
The GLB's flow UVs and junction geometry were checked from the binary export.
Runtime rendering in Wilderness remains unverified.

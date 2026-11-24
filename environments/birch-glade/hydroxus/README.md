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

## Refraction

To refract the lit riverbed and submerged rocks, apply the
[opaque scene-color patch](opaque-scene-color.patch) to Hydroxus at
`63b5452ff361c0b5d30a65cfbf485e1267eaf935`. Run `git apply` with that
file from the Hydroxus checkout. The renderer takes one HDR color snapshot
per view before the forward pass when a visible material requests it and its
`sceneColorWeight` is positive. Materials that omit that property keep the
default scene-color capture behavior.

Point Wilderness and its graphics dependency at the same patched checkout.
For a local test, add this to the Wilderness workspace manifest, adjusting
the paths to your Hydroxus checkout:

```toml
[patch."https://github.com/d4140n-4h3-1/Hydroxus.git"]
fyrox = { path = "../Hydroxus/fyrox" }
fyrox-graphics-wgpu = { path = "../Hydroxus/fyrox-graphics-wgpu" }
```

After attaching the materials, enable refraction on both waterways:

```rust
river.set_refraction_strength(1.0);
stream.set_refraction_strength(1.0);
```

The strength defaults to zero for compatibility with stock Hydroxus. The
shader uses water's index of refraction (1.333) and the animated surface normal
to redirect a sample of the opaque scene. It uses scene depth to fade the
offset in shallows and reject samples that would pull near-bank geometry
across the water. Refraction samples opaque surfaces visible in the current
camera view.

At full strength the shader still fades refraction with bed depth, view
distance, and grazing angle. It uses one color sample where refraction is
active. The shallow-water light pattern modulates that sample and uses the
same current waves as the surface. Foam is evaluated only in shallow contact
bands, and shared waves are evaluated only near configured confluences.
The sun direction also dims the procedural reflection and foam at night.

In a 960 × 540 offscreen software Vulkan test containing banks, shallows,
deep water, and a confluence, the median draw dropped from 16.98 ms to
12.64 ms with refraction enabled and from 12.60 ms to 5.28 ms with it disabled.
The test isolates the water draw and excludes the HDR snapshot and other
Wilderness rendering.

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
Place the cursor at the source, select the terrain, and run **Trace River
and Bed from 3D Cursor**. One operation traces the slope, cuts the channel,
writes the flow UVs, and shapes the submerged terrain into gravel bars and
scoured runs. **Bed Seed** controls the relief and the embedded gravel
placement. Gravel is batched into one opaque mesh capped at 480 stones, with an embedded stone texture atlas.

After editing a paired ribbon, call `hydroxus_rivers.set_water_uv(water_object)`
before joining or exporting. A scripted build that needs to join several
channels can call `hx.river(build_bed=False)` for each trace, then
`hydroxus_rivers.dress_channel_beds(terrain, waterways, seed, collection)` once
after joining. Birch Glade uses its shoreline seed for the bed as well.

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
offscreen. Offscreen Vulkan draws verified the depth response and displacement
of an opaque test pattern. The renderer patch was checked against the pinned
revision.
The GLB's flow UVs and junction geometry were checked from the binary export.
Runtime rendering in Wilderness remains unverified.

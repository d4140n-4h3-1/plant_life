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
water meets banks and submerged rocks. The water mesh stays fixed. A level optical normal keeps triangles in the
water ribbon from imprinting their slopes on the reflected highlights.

For a day/night cycle, call `set_sun_direction` with the world-space vector from
the water toward the sun. Supply the directional light's world-space +Y axis
when using Wilderness's convention. The material expects opaque terrain and rocks
to write depth before the forward water pass, and uses perspective camera depth.

## Obstacle ripples

Pass the world-space bounds of obstacle meshes or colliders to each liquid
controller. Refresh the bounds after physics updates for moving objects.
The controller caches the liquid triangles when attached, tests a few vertical
segments through each obstacle against that surface, and keeps up to eight
contacts nearest the viewer. Objects entirely above or below the sampled
surface do not emit ripples.

```rust
river.update_obstacles(river_mesh, &obstacle_world_bounds, camera_position);
river.update(context.dt);
```

Call the same methods for ponds, springs, and other horizontal liquid surfaces.
The footprint of each ripple is an ellipse fitted to the obstacle bounds.
The rings affect both highlights and refraction. They stay anchored at the
obstacle and stretch downstream along increasing `FlowUV.u`, with closer
spacing upstream. Distortion eases at a confluence where the channels'
directions change. Slow pond settings leave the rings symmetric.

The controller infers a default current strength from its signed phase rate
and treats rates up to 0.06 cycles per second as still water for obstacle
ripples. Call `set_obstacle_current` with a value from −1 to 1 to set the
stretch independently. Zero gives symmetric rings, and a negative value
reverses the current. Ripple propagation continues even at zero current.
The effect fades with distance and uses no additional texture samples. This is a visual contact response and
does not apply buoyancy or change rigid-body motion.

## Ponds and springs

In the Blender **Rivers, Streams and Ponds** panel, choose **Pond** or **Spring**,
set the two radii and the shared depth and bed seed, then run **Create Pond or
Spring at 3D Cursor**. Select a terrain mesh dense enough to resolve the shallow
shelf before running the operator. Spring mode leaves an outlet in the rim and
records its location. Connect a downstream trace at that outlet to make a
continuous surface.

Birch Glade includes **Heather Pond**, a closed woodland basin, and
**Alder Spring**, which feeds Fern Stream. Both use level water surfaces and
share the scene's textured gravel mesh with the channels. The Blender file
includes a camera for each basin.

In Hydroxus, use a low phase rate for each still-water surface and reduce its
ripple height and foam:

```rust
let pond = FlowingWater::attach(pond_mesh, WaterBackend::Wgpu, 0.035)?;
pond.set_surface_activity(0.30, 0.0);
let spring = FlowingWater::attach(spring_mesh, WaterBackend::Wgpu, 0.10)?;
spring.set_surface_activity(0.52, 0.16);
```

## Refraction

To refract the lit riverbed and submerged rocks, apply the
[opaque scene-color patch](opaque-scene-color.patch) to Hydroxus at
`63b5452ff361c0b5d30a65cfbf485e1267eaf935`. Run `git apply` with that
file from the Hydroxus checkout. The renderer takes one HDR color snapshot
per view before the forward pass when a visible material requests it and either its
`sceneColorWeight` or `reflectionWeight` is positive. Materials with neither
weight keep the default scene-color capture behavior.

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
pond.set_refraction_strength(1.0);
spring.set_refraction_strength(1.0);
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

### Close-up surface detail

World-space fine ripples break up the highlight independently of the channel
mesh, with varying strength across the surface. The ripples are filtered
against their projected pixel size to reduce shimmer. Foam uses broken
filaments inside the existing shallow contact band, and the small caustic
variation reuses the bed sample. The detail adds no texture reads to the
reflection or refraction paths. Use `set_surface_activity` to soften ripples
and foam in calmer water.

### Nearby reflections

With the same renderer patch, opt in to nearby scenery reflections. Calm
surfaces make the strongest use of this effect:

```rust
river.set_reflection_strength(0.55);
stream.set_reflection_strength(0.35);
spring.set_reflection_strength(0.60);
pond.set_reflection_strength(0.78);
```

The reflection path shares the refraction snapshot. It uses at most three
depth lookups over 4.4 m and one color lookup on a hit. It fades out with
camera distance, view angle, weak intersections, and proximity to a screen
edge. Misses fall back to the procedural sky. A strength of zero skips the
trace and is the default. Geometry outside the current camera frame is not
available for this effect.

## Joining water surfaces

Birch Glade's tributary mesh is trimmed to the receiving bank and eased into
the river's surface height. The two meshes meet without overlapping translucent
faces. In the game, register the same world-space junction on both controllers
so the ripples and foam transition to one shared pattern at the seam.

```rust
use fyrox::core::algebra::Vector4;

// Birch Glade at its original import transform. xyz is the center, w the radius.
let river_join = Vector4::new(-6.537, 0.809, -5.368, 2.2);
let spring_join = Vector4::new(-11.065, 1.815, -5.628, 3.0);
river.set_confluences(&[river_join]);
stream.set_confluences(&[river_join, spring_join]);
spring.set_confluences(&[spring_join]);
```

Each update, call `set_confluence_time(context.elapsed_time)` on the three connected
controllers, in addition to their regular `update(context.dt)` calls. If you move the imported
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

Use the variant's `join_center_local` and `spring_join_center_blender_world`
when setting its shader confluences.
The seed is recorded in each water node's GLB extras as `shore_seed`.

The forward renderer and scene-depth binding were checked against Wilderness's
pinned Hydroxus Vulkan revision, `63b5452`. Both shader stages were compiled
offscreen. Offscreen Vulkan draws verified the depth response and displacement
of an opaque test pattern. The renderer patch was checked against the pinned
revision.
The GLB's flow UVs and junction geometry were checked from the binary export.
Runtime rendering in Wilderness remains unverified.

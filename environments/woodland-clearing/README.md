# Woodland clearing

A 26 × 34 m woodland scene with a winding dirt footpath, gently uneven terrain, and all four plants from the collection. The reference layout has eight pines, eight Norway spruces, 41 bilberry shrubs, and 247 sheep fescue tufts.

- [Blender scene](woodland-clearing.blend) includes linked plant meshes, packed textures, daylight, and two cameras.
- [GLB scene](woodland-clearing.glb) includes the terrain and plant placements in meters. All plant placements share four mesh definitions.
- [Trail view](renders/woodland-trail.png) shows the scene from the path. [Canopy view](renders/woodland-overview.png) shows the layout from above.
- [Ground maps](textures) includes the terrain base color, normal, packed ORM, and height maps.

For games, each plant node carries a species identifier. Render the plants using their respective materials and the collection's [Vulkan vertex wind shader](../../assets/conifers/pine/tools/pine_wind.vert.spv). Use the original local mesh height and a different phase per placement. Apply the appropriate foliage alpha mask in main, shadow, and depth passes.

## Rebuild

Run Blender 4.3 from the repository root.

```sh
blender --background --python-exit-code 1 \
  --python environments/woodland-clearing/tools/build_woodland.py
```

Use `-- --seed 17` to change the understory placement. Use `-- --output-dir PATH --no-renders` for a model-only build in another folder.

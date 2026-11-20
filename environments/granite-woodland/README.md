# Granite woodland

A **28 × 37 m** rocky woodland scene with an uphill forest-loam trail. Granite boulders and slabs line the banks, with cobbles, ferns, grasses, heather, bluebells, and daisies around the five canopy species.

| Group | Placements |
| --- | ---: |
| Canopy trees | 18 |
| Granite rocks | 91 |
| Shrubs | 28 |
| Ferns | 62 |
| Grasses | 224 |
| Wildflowers | 44 |

- [Blender scene](granite-woodland.blend) includes packed textures, seven named collections, daylight, and two cameras.
- [GLB scene](granite-woodland.glb) includes 467 placements and the terrain, with 17 shared mesh definitions in meters. The terrain uses forest loam at one repeat per meter and vertex colors for the trail and forest floor.
- [Trail render](renders/granite-trail.png) and [overhead render](renders/granite-overhead.png) show the layout from both cameras.

The vegetation nodes have `wind: true` metadata. They can use the collection's [Vulkan wind shader](../../assets/conifers/pine/tools/pine_wind.vert.spv) with local mesh height and per-instance phase. Rock nodes are marked `wind: false`.

## Rebuild

Run Blender 4.3 from the repository root.

```sh
blender --background --python-exit-code 1 \
  --python environments/granite-woodland/tools/build_granite_woodland.py
```

Use `-- --seed 27` to vary the undergrowth, smaller stone placement, and instance proportions. Use `-- --output-dir PATH --no-renders` to write the models to another folder.

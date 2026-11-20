# Silver fir

*Abies alba*. Long, nearly horizontal boughs carry flat, dark needle sprays. Upright cones sit on the upper branches. The reference tree is **12.6 m** tall and uses **10,214 triangles** with a ground-level pivot.

`silver-fir.blend` contains the editable Z-up model with packed textures. `silver-fir.glb` is the Y-up game asset in meters. `textures/` includes 512 × 512 base color, tangent-space normal, ORM, and height maps for bark, needles, and cones. `renders/` contains full-tree and branch-detail views.

The needle material is double-sided with a 0.40 alpha cutoff. The three materials share one UV set. The GLB supplies the vertex attributes used by the [Vulkan wind shader](../pine/tools/pine_wind.vert.spv). Set its local height to the height of the selected seed or reference.

## Build

Run from the repository root with Blender 4.3.

```sh
blender --background --python-exit-code 1 \
  --python assets/conifers/silver-fir/tools/build_silver_fir.py

blender --background --python-exit-code 1 \
  --python assets/conifers/silver-fir/tools/build_silver_fir.py -- --seed 31 --no-renders
```

Use `--random` to pick a seed or `--output-dir PATH` to set a destination. Seeded variants default to `variants/` and vary height, width, lean, and branching.

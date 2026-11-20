# Meadow foxtail

*Alopecurus pratensis*. A meadow grass with broad, arching blades and dense cylindrical seed heads. The reference plant is **0.82 m** tall and uses **2,405 triangles**, with a ground-level pivot.

| File | Contents |
| --- | --- |
| [meadow-foxtail.blend](meadow-foxtail.blend) | Editable Z-up Blender model with packed textures |
| [meadow-foxtail.glb](meadow-foxtail.glb) | Y-up mesh in meters with embedded textures |
| [Textures](textures) | 512 × 512 base color, normal, ORM, and height maps |
| [Full view](renders/meadow-foxtail-full.png) | Overall silhouette |
| [Detail](renders/meadow-foxtail-detail.png) | Surface and foliage detail |

Stems, cutout blades, and opaque seed heads. The model has one UV set. Cutout materials are double-sided and use a 0.40 alpha cutoff. The GLB provides the vertex attributes expected by the [Vulkan wind shader](../../conifers/pine/tools/pine_wind.vert.spv). Use the local height of the selected variant.

## Build

Use Blender 4.3 from the repository root.

```sh
blender --background --python-exit-code 1 \
  --python assets/grasses/meadow-foxtail/tools/build_meadow_foxtail.py

blender --background --python-exit-code 1 \
  --python assets/grasses/meadow-foxtail/tools/build_meadow_foxtail.py -- --seed 27 --no-renders
```

Use `--random` to choose a new seed, or `--output-dir PATH` to set a destination. Seeded variants change plant proportions and branch, blade, or flower arrangement.

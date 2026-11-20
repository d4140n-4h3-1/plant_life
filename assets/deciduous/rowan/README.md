# Rowan

*Sorbus aucuparia*. A rounded deciduous canopy with pinnate foliage, gray bark, and red-orange berry clusters. The reference plant is **9.72 m** tall and uses **10,160 triangles**, with a ground-level pivot.

| File | Contents |
| --- | --- |
| [rowan.blend](rowan.blend) | Editable Z-up Blender model with packed textures |
| [rowan.glb](rowan.glb) | Y-up mesh in meters with embedded textures |
| [Textures](textures) | 512 × 512 base color, normal, ORM, and height maps |
| [Full view](renders/rowan-full.png) | Overall silhouette |
| [Detail](renders/rowan-detail.png) | Surface and foliage detail |

Bark, cutout foliage, and berries. The model has one UV set. Cutout materials are double-sided and use a 0.40 alpha cutoff. The GLB provides the vertex attributes expected by the [Vulkan wind shader](../../conifers/pine/tools/pine_wind.vert.spv). Use the local height of the selected variant.

The [bark source swatch](source/) is included.

## Build

Use Blender 4.3 from the repository root.

```sh
blender --background --python-exit-code 1 \
  --python assets/deciduous/rowan/tools/build_rowan.py

blender --background --python-exit-code 1 \
  --python assets/deciduous/rowan/tools/build_rowan.py -- --seed 27 --no-renders
```

Use `--random` to choose a new seed, or `--output-dir PATH` to set a destination. Seeded variants change plant proportions and branch, blade, or flower arrangement.

# Wood sorrel

*Oxalis acetosella*. Low woodland ground cover with three heart-shaped leaflets per stem and small white, pink-veined flowers. The reference plant is **0.19 m** tall, uses **1,821 triangles**, and has a ground-level pivot.

| File | Contents |
| --- | --- |
| [wood-sorrel.blend](wood-sorrel.blend) | Editable Z-up Blender model with packed textures |
| [wood-sorrel.glb](wood-sorrel.glb) | Y-up mesh in meters with embedded textures |
| [Textures](textures) | 512 × 512 base color, tangent-space normal, ORM, and height maps for the leaves, stems, and flowers |
| [Full plant](renders/sorrel-full.png) | Overall silhouette |
| [Flower detail](renders/sorrel-detail.png) | Flower and foliage detail |

The mesh uses a single UV set. The leaves use double-sided cutouts with a 0.40 alpha cutoff. Stems and flowers use opaque geometry. Base color uses sRGB. Normal and ORM use linear sampling. The GLB supplies the vertex attributes for the [Vulkan wind shader](../../conifers/pine/tools/pine_wind.vert.spv). Set the local height to match the selected model.

## Build

Use Blender 4.3 from the repository root.

```sh
blender --background --python-exit-code 1 \
  --python assets/wildflowers/wood-sorrel/tools/build_wood_sorrel.py

blender --background --python-exit-code 1 \
  --python assets/wildflowers/wood-sorrel/tools/build_wood_sorrel.py -- --seed 27 --no-renders
```

Use `--random` to choose a new seed or `--output-dir PATH` to choose the output location. Seeded models vary height, spread, flower placement, and leaf orientation.

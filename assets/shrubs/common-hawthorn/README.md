# Common hawthorn

*Crataegus monogyna*. A dense hedgerow shrub with small lobed leaves, woody stems, and clusters of red haws. The reference plant is **2.83 m** tall and uses **8,361 triangles**, with a ground-level pivot.

| File | Contents |
| --- | --- |
| [common-hawthorn.blend](common-hawthorn.blend) | Editable Z-up Blender model with packed textures |
| [common-hawthorn.glb](common-hawthorn.glb) | Y-up mesh in meters with embedded textures |
| [Textures](textures) | 12 maps at 512 × 512, covering base color, normal, ORM, and height |
| [Full plant](renders/common-hawthorn-full.png) | Overall silhouette |
| [Detail](renders/common-hawthorn-detail.png) | Bark, foliage, and branch detail |

The GLB uses one UV set and a double-sided leaf material with a 0.40 alpha cutoff. Its vertex attributes match the collection's [Vulkan wind shader](../../conifers/pine/tools/pine_wind.vert.spv). Pass the height of the specific plant and a distinct phase per instance.

## Build

Use Blender 4.3 from the repository root.

```sh
blender --background --python-exit-code 1 \
  --python assets/shrubs/common-hawthorn/tools/build_common_hawthorn.py

blender --background --python-exit-code 1 \
  --python assets/shrubs/common-hawthorn/tools/build_common_hawthorn.py -- --seed 27 --no-renders
```

Use `--random` to choose a new seed and `--output-dir PATH` to set a destination. Seeded variants change height, spread, and branching.

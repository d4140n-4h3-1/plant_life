# English oak

*Quercus robur*. A broad, rounded canopy above a thick trunk and spreading limbs. The foliage atlas gives the individual leaves their rounded lobes. The reference plant is **10.85 m** tall and uses **6,540 triangles**, with a ground-level pivot.

| File | Contents |
| --- | --- |
| [english-oak.blend](english-oak.blend) | Editable Z-up Blender model with packed textures |
| [english-oak.glb](english-oak.glb) | Y-up mesh in meters with embedded textures |
| [Textures](textures) | 8 maps at 512 × 512, covering base color, normal, ORM, and height |
| [Full plant](renders/english-oak-full.png) | Overall silhouette |
| [Detail](renders/english-oak-detail.png) | Bark, foliage, and branch detail |

The GLB uses one UV set and a double-sided leaf material with a 0.40 alpha cutoff. Its vertex attributes match the collection's [Vulkan wind shader](../../conifers/pine/tools/pine_wind.vert.spv). Pass the height of the specific plant and a distinct phase per instance.

The [bark source swatch](source/) is included.

## Build

Use Blender 4.3 from the repository root.

```sh
blender --background --python-exit-code 1 \
  --python assets/deciduous/english-oak/tools/build_english_oak.py

blender --background --python-exit-code 1 \
  --python assets/deciduous/english-oak/tools/build_english_oak.py -- --seed 27 --no-renders
```

Use `--random` to choose a new seed and `--output-dir PATH` to set a destination. Seeded variants change height, spread, and branching.

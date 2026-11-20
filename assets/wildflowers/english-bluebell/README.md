# English bluebell

*Hyacinthoides non-scripta*. A woodland clump with narrow basal leaves and curved, one-sided spikes of hollow violet-blue bells. The reference model is **0.41 m** tall and uses **4,975 triangles**, with a ground-level pivot.

| File | Contents |
| --- | --- |
| [english-bluebell.blend](english-bluebell.blend) | Editable Z-up Blender model with packed textures |
| [english-bluebell.glb](english-bluebell.glb) | Y-up mesh in meters with embedded textures |
| [Textures](textures) | 12 maps at 512 × 512, covering base color, normal, ORM, and height |
| [Full plant](renders/english-bluebell-full.png) | Overall silhouette |
| [Flower detail](renders/english-bluebell-detail.png) | Petals, stems, and foliage detail |

The mesh uses one UV set. Leaves use double-sided cutouts with a 0.40 alpha cutoff. Flowers use opaque geometry. The GLB supplies the vertex attributes expected by the [Vulkan wind shader](../../conifers/pine/tools/pine_wind.vert.spv). Pass the local height of the selected plant.

## Build

Use Blender 4.3 from the repository root.

```sh
blender --background --python-exit-code 1 \
  --python assets/wildflowers/english-bluebell/tools/build_english_bluebell.py

blender --background --python-exit-code 1 \
  --python assets/wildflowers/english-bluebell/tools/build_english_bluebell.py -- --seed 27 --no-renders
```

Use `--random` to choose a new seed or `--output-dir PATH` to set the destination. Seeded variants change the shape, height, and flower arrangement.

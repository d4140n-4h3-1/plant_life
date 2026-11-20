# Common poppy

*Papaver rhoeas*. A meadow and field-edge clump with toothed foliage, four scarlet petals per flower, and dark pollen centers. The reference model is **0.68 m** tall and uses **1,900 triangles**, with a ground-level pivot.

| File | Contents |
| --- | --- |
| [common-poppy.blend](common-poppy.blend) | Editable Z-up Blender model with packed textures |
| [common-poppy.glb](common-poppy.glb) | Y-up mesh in meters with embedded textures |
| [Textures](textures) | 16 maps at 512 × 512, covering base color, normal, ORM, and height |
| [Full plant](renders/common-poppy-full.png) | Overall silhouette |
| [Flower detail](renders/common-poppy-detail.png) | Petals, stems, and foliage detail |

The mesh uses one UV set. Leaves use double-sided cutouts with a 0.40 alpha cutoff. Flowers use opaque geometry. The GLB supplies the vertex attributes expected by the [Vulkan wind shader](../../conifers/pine/tools/pine_wind.vert.spv). Pass the local height of the selected plant.

## Build

Use Blender 4.3 from the repository root.

```sh
blender --background --python-exit-code 1 \
  --python assets/wildflowers/common-poppy/tools/build_common_poppy.py

blender --background --python-exit-code 1 \
  --python assets/wildflowers/common-poppy/tools/build_common_poppy.py -- --seed 27 --no-renders
```

Use `--random` to choose a new seed or `--output-dir PATH` to set the destination. Seeded variants change the shape, height, and flower arrangement.

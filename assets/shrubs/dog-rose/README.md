# Dog rose

*Rosa canina*. An open, arching wild rose with tapered prickles, pinnate leaf sprays, and pink five-petaled flowers. The reference bush is **1.96 m** tall and uses **8,591 triangles**, with a ground-level pivot.

| File | Contents |
| --- | --- |
| [dog-rose.blend](dog-rose.blend) | Editable Z-up Blender model with packed textures |
| [dog-rose.glb](dog-rose.glb) | Y-up mesh in meters with embedded textures |
| [Textures](textures) | 512 × 512 base color, normal, ORM, and height maps |
| [Full bush](renders/dog-rose-full.png) | Overall silhouette |
| [Flower detail](renders/dog-rose-detail.png) | Petals, yellow centers, and leaf sprays |

The mesh uses one UV set and four materials for the canes, leaves, petals, and pollen. Leaf sprays use double-sided cutouts with a 0.40 alpha cutoff. Flowers are modeled as geometry. The GLB provides the vertex attributes expected by the [Vulkan wind shader](../../conifers/pine/tools/pine_wind.vert.spv). Pass the local height for the chosen seed.

## Build

Use Blender 4.3 from the repository root.

```sh
blender --background --python-exit-code 1 \
  --python assets/shrubs/dog-rose/tools/build_dog_rose.py

blender --background --python-exit-code 1 \
  --python assets/shrubs/dog-rose/tools/build_dog_rose.py -- --seed 27 --no-renders
```

Use `--random` to choose a new seed or `--output-dir PATH` to set the destination. Variants vary cane shape, foliage orientation, flower size, and total height.

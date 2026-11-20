# Common broom

*Cytisus scoparius*. A spring-flowering shrub with upright green stems, small groups of three leaflets, and bright yellow pea flowers. The reference plant is **1.91 m** tall and uses **2,528 triangles** with a ground-level pivot.

| File | Contents |
| --- | --- |
| [common-broom.blend](common-broom.blend) | Editable Blender model with packed textures |
| [common-broom.glb](common-broom.glb) | Y-up mesh in meters with embedded textures |
| [Textures](textures) | 512 × 512 base color, tangent-space normal, ORM, and height maps |
| [Full plant](renders/broom-full.png) | Overall shape |
| [Detail](renders/broom-detail.png) | Foliage and shoot detail |

The three materials cover stems, leaves, and flowers. Leaves and flowers use double-sided cutouts with a 0.40 alpha cutoff. The mesh uses one UV set. The GLB supplies the vertex attributes for the collection's [Vulkan wind shader](../../conifers/pine/tools/pine_wind.vert.spv). Pass the selected plant's local height and a distinct phase per instance.

## Build

Use Blender 4.3 from the repository root.

```sh
blender --background --python-exit-code 1 \
  --python assets/shrubs/common-broom/tools/build_common_broom.py

blender --background --python-exit-code 1 \
  --python assets/shrubs/common-broom/tools/build_common_broom.py -- --seed 27 --no-renders
```

Use `--random` to choose a new seed and `--output-dir PATH` to choose a destination. Otherwise, seeded outputs go into `variants/`. Variants change size, spread, and shoot arrangement.

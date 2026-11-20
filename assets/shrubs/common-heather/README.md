# Common heather

*Calluna vulgaris*. A late-summer mound with low green growth, reddish stems, and sprays of pink flowers. The reference model stands **0.61 m** tall, uses **1,680 triangles**, and has a ground-level pivot.

| File | Contents |
| --- | --- |
| [common-heather.blend](common-heather.blend) | Editable Blender model with packed textures |
| [common-heather.glb](common-heather.glb) | Y-up mesh in meters with embedded textures |
| [Textures](textures) | 512 × 512 base color, tangent-space normal, ORM, and height maps |
| [Full render](renders/heather-full.png) | Overall shape |
| [Detail render](renders/heather-detail.png) | Surface and silhouette details |

Stems, cutout greenery, and cutout blossoms. The asset uses one UV set. Base color uses sRGB. Normal and ORM use linear sampling. The GLB provides the vertex attributes used by the collection's [Vulkan wind shader](../../conifers/pine/tools/pine_wind.vert.spv). Supply the local height of the specific variant.

Both foliage materials use a 0.40 alpha cutoff.

## Build

From the repository root, use Blender 4.3.

```sh
blender --background --python-exit-code 1 \
  --python assets/shrubs/common-heather/tools/build_common_heather.py

blender --background --python-exit-code 1 \
  --python assets/shrubs/common-heather/tools/build_common_heather.py -- --seed 27 --no-renders
```

Use `--random` to choose a new seed. Variants go under `variants/` unless you set `--output-dir`. Seeds vary dimensions and plant geometry.

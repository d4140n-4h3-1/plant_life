# Silver birch

*Betula pendula*. Pale papery bark and an airy crown of serrated broad leaves on fine, drooping branchlets. The reference model stands **12.70 m** tall, uses **6,180 triangles**, and has a ground-level pivot.

| File | Contents |
| --- | --- |
| [silver-birch.blend](silver-birch.blend) | Editable Blender model with packed textures |
| [silver-birch.glb](silver-birch.glb) | Y-up mesh in meters with embedded textures |
| [Textures](textures) | 512 × 512 base color, tangent-space normal, ORM, and height maps |
| [Full render](renders/birch-full.png) | Overall shape |
| [Detail render](renders/birch-detail.png) | Surface and silhouette details |

Bark and cutout leaves. The asset uses one UV set. Base color uses sRGB. Normal and ORM use linear sampling. The GLB provides the vertex attributes used by the collection's [Vulkan wind shader](../../conifers/pine/tools/pine_wind.vert.spv). Supply the local height of the specific variant.

The [bark source swatch](source/) is included. The leaves use a 0.40 alpha cutoff.

## Build

From the repository root, use Blender 4.3.

```sh
blender --background --python-exit-code 1 \
  --python assets/deciduous/silver-birch/tools/build_silver_birch.py

blender --background --python-exit-code 1 \
  --python assets/deciduous/silver-birch/tools/build_silver_birch.py -- --seed 27 --no-renders
```

Use `--random` to choose a new seed. Variants go under `variants/` unless you set `--output-dir`. Seeds vary dimensions and plant geometry.

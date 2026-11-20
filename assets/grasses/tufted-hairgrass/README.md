# Tufted hairgrass

*Deschampsia cespitosa*. A meadow and woodland-edge grass with long arching blades and loose bronze seed panicles. The reference model stands **0.96 m** tall, uses **1,800 triangles**, and has a ground-level pivot.

| File | Contents |
| --- | --- |
| [tufted-hairgrass.blend](tufted-hairgrass.blend) | Editable Blender model with packed textures |
| [tufted-hairgrass.glb](tufted-hairgrass.glb) | Y-up mesh in meters with embedded textures |
| [Textures](textures) | 512 × 512 base color, tangent-space normal, ORM, and height maps |
| [Full render](renders/hairgrass-full.png) | Overall shape |
| [Detail render](renders/hairgrass-detail.png) | Surface and silhouette details |

A single double-sided blade and seed atlas. The asset uses one UV set. Base color uses sRGB. Normal and ORM use linear sampling. The GLB provides the vertex attributes used by the collection's [Vulkan wind shader](../../conifers/pine/tools/pine_wind.vert.spv). Supply the local height of the specific variant.

## Build

From the repository root, use Blender 4.3.

```sh
blender --background --python-exit-code 1 \
  --python assets/grasses/tufted-hairgrass/tools/build_tufted_hairgrass.py

blender --background --python-exit-code 1 \
  --python assets/grasses/tufted-hairgrass/tools/build_tufted_hairgrass.py -- --seed 27 --no-renders
```

Use `--random` to choose a new seed. Variants go under `variants/` unless you set `--output-dir`. Seeds vary dimensions and plant geometry.

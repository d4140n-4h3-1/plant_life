# Hard fern

*Struthiopteris spicant*. A compact rosette of narrow, feather-like fronds for shaded ground. The reference plant is **0.45 m** tall, uses **3,264 triangles**, and has a ground-level pivot.

| File | Contents |
| --- | --- |
| [hard-fern.blend](hard-fern.blend) | Editable Z-up Blender model with packed textures |
| [hard-fern.glb](hard-fern.glb) | Y-up game mesh in meters with embedded textures |
| [Textures](textures) | 512 × 512 base color, tangent-space normal, ORM, and height maps for fronds and stalks |
| [Full plant](renders/hard-fern-full.png) | Overall silhouette |
| [Frond detail](renders/hard-fern-detail.png) | Leaflet shape and vein detail |

The mesh uses one UV set. Fronds use double-sided cutouts with a 0.40 alpha cutoff. Base color uses sRGB. Normal and ORM use linear sampling. The GLB exposes the attributes used by the [Vulkan wind shader](../../conifers/pine/tools/pine_wind.vert.spv). Use the actual model height and a distinct phase per instance.

## Build

Run from the repository root with Blender 4.3.

```sh
blender --background --python-exit-code 1 \
  --python assets/ferns/hard-fern/tools/build_hard_fern.py

blender --background --python-exit-code 1 \
  --python assets/ferns/hard-fern/tools/build_hard_fern.py -- --seed 27 --no-renders
```

Use `--random` to choose a new seed or `--output-dir PATH` to set the output folder. Seeded variants change frond shape, orientation, height, and spread.

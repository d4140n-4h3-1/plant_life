# Bracken

*Pteridium aquilinum*. Taller arching stalks with broad, divided fronds for woodland edges and clearings. The reference plant is **0.92 m** tall, uses **1,024 triangles**, and has a ground-level pivot.

| File | Contents |
| --- | --- |
| [bracken.blend](bracken.blend) | Editable Z-up Blender model with packed textures |
| [bracken.glb](bracken.glb) | Y-up game mesh in meters with embedded textures |
| [Textures](textures) | 512 × 512 base color, tangent-space normal, ORM, and height maps for fronds and stalks |
| [Full plant](renders/bracken-full.png) | Overall silhouette |
| [Frond detail](renders/bracken-detail.png) | Leaflet shape and vein detail |

The mesh uses one UV set. Fronds use double-sided cutouts with a 0.40 alpha cutoff. Base color uses sRGB. Normal and ORM use linear sampling. The GLB exposes the attributes used by the [Vulkan wind shader](../../conifers/pine/tools/pine_wind.vert.spv). Use the actual model height and a distinct phase per instance.

## Build

Run from the repository root with Blender 4.3.

```sh
blender --background --python-exit-code 1 \
  --python assets/ferns/bracken/tools/build_bracken.py

blender --background --python-exit-code 1 \
  --python assets/ferns/bracken/tools/build_bracken.py -- --seed 27 --no-renders
```

Use `--random` to choose a new seed or `--output-dir PATH` to set the output folder. Seeded variants change frond shape, orientation, height, and spread.

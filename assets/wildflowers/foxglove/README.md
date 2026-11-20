# Foxglove

*Digitalis purpurea*. A basal rosette and three tall flowering spikes. Each pink bell has an open lip and a textured, spotted throat. The reference plant is **1.49 m** tall, uses **7,809 triangles**, and has a ground-level pivot.

| File | Contents |
| --- | --- |
| [foxglove.blend](foxglove.blend) | Editable Z-up Blender model with packed textures |
| [foxglove.glb](foxglove.glb) | Y-up mesh in meters with embedded textures |
| [Textures](textures) | 512 × 512 base color, tangent-space normal, ORM, and height maps for the leaves, stems, and flowers |
| [Full plant](renders/foxglove-full.png) | Overall silhouette |
| [Flower detail](renders/foxglove-detail.png) | Flower and foliage detail |

The mesh uses a single UV set. The leaves use double-sided cutouts with a 0.40 alpha cutoff. Stems and flowers use opaque geometry. Base color uses sRGB. Normal and ORM use linear sampling. The GLB supplies the vertex attributes for the [Vulkan wind shader](../../conifers/pine/tools/pine_wind.vert.spv). Set the local height to match the selected model.

## Build

Use Blender 4.3 from the repository root.

```sh
blender --background --python-exit-code 1 \
  --python assets/wildflowers/foxglove/tools/build_foxglove.py

blender --background --python-exit-code 1 \
  --python assets/wildflowers/foxglove/tools/build_foxglove.py -- --seed 27 --no-renders
```

Use `--random` to choose a new seed or `--output-dir PATH` to choose the output location. Seeded models vary height, spread, flower placement, and leaf orientation.

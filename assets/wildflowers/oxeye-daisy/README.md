# Oxeye daisy

*Leucanthemum vulgare*. A flowering clump with white ray petals and raised yellow centers on slender stems. The reference plant is **0.55 m** tall and uses **3,454 triangles**, with a ground-level pivot.

| File | Contents |
| --- | --- |
| [oxeye-daisy.blend](oxeye-daisy.blend) | Editable Z-up Blender model with packed textures |
| [oxeye-daisy.glb](oxeye-daisy.glb) | Y-up mesh in meters with embedded textures |
| [Textures](textures) | 512 × 512 base color, normal, ORM, and height maps |
| [Full view](renders/oxeye-daisy-full.png) | Overall silhouette |
| [Detail](renders/oxeye-daisy-detail.png) | Surface and foliage detail |

Stems, cutout leaves, petals, and pollen discs. The model has one UV set. Cutout materials are double-sided and use a 0.40 alpha cutoff. The GLB provides the vertex attributes expected by the [Vulkan wind shader](../../conifers/pine/tools/pine_wind.vert.spv). Use the local height of the selected variant.

## Build

Use Blender 4.3 from the repository root.

```sh
blender --background --python-exit-code 1 \
  --python assets/wildflowers/oxeye-daisy/tools/build_oxeye_daisy.py

blender --background --python-exit-code 1 \
  --python assets/wildflowers/oxeye-daisy/tools/build_oxeye_daisy.py -- --seed 27 --no-renders
```

Use `--random` to choose a new seed, or `--output-dir PATH` to set a destination. Seeded variants change plant proportions and branch, blade, or flower arrangement.

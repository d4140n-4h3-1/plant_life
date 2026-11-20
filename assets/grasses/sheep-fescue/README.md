# Sheep fescue

A tuft of *Festuca ovina* with fine, curved blades, several dry seed heads, and a ground-level pivot. The reference tuft is about 35 cm tall and 52 cm across. It uses 938 triangles and a single double-sided material.

| File | Contents |
| --- | --- |
| [sheep-fescue.glb](sheep-fescue.glb) | Y-up game mesh in meters with embedded textures |
| [sheep-fescue.blend](sheep-fescue.blend) | Editable Z-up model with packed textures |
| [Textures](textures) | 512 × 512 base color, normal, ORM, and height maps |
| [Full tuft](renders/fescue-full.png) | Blade shape and density |
| [Seed heads](renders/fescue-detail.png) | Close-up showing blades and dry stems |
| [Scatter example](renders/fescue-patch.png) | A small patch scattered from five shared meshes |

Blade silhouettes come from geometry. The shared atlas provides fresh, weathered, and dry color bands on one UV set. Base color uses sRGB. Normal and ORM use linear sampling. ORM packs occlusion, roughness, and metallic into red, green, and blue.

## Build and scatter

From the repository root, run Blender 4.3 with:

```sh
blender --background --python-exit-code 1 \
  --python assets/grasses/sheep-fescue/tools/build_fescue.py

blender --background --python-exit-code 1 \
  --python assets/grasses/sheep-fescue/tools/build_fescue.py -- --seed 27 --no-renders

blender --background --python-exit-code 1 \
  --python assets/grasses/sheep-fescue/tools/render_patch.py -- --seed 27
```

Use `--random` to choose a new tuft seed. Seeds vary blade lengths, curvature, height, and spread. The build tool puts variants in `variants/` by default or accepts `--output-dir`. The grass can use the repository's [Vulkan wind shader](../../conifers/pine/tools/pine_wind.vert.spv) with the tuft's local height and a different phase per instance.

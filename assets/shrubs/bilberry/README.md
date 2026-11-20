# Bilberry shrub

A fruiting European bilberry (*Vaccinium myrtillus*) for forest understory. The reference shrub is approximately 0.68 m tall and 0.80 m wide. It uses 7,657 triangles and has a ground-level pivot.

| File | Contents |
| --- | --- |
| [bilberry.glb](bilberry.glb) | Y-up mesh in meters with three materials and embedded PBR textures |
| [bilberry.blend](bilberry.blend) | Editable Z-up Blender model with packed textures |
| [textures](textures) | 512 × 512 base color, normal, ORM, and height maps for leaves, stems, and berries |
| [Full render](renders/bilberry-full.png) | Shrub shape and foliage |
| [Detail render](renders/bilberry-detail.png) | Leaf serrations, veins, fine stems, and fruit |

The procedural leaf atlas uses two colorways and a double-sided alpha mask with a cutoff of 0.40. The mesh uses one UV set and shares atlas space across leaves. Base color uses sRGB. Normal and ORM textures use linear sampling. ORM packs occlusion, roughness, and metallic in red, green, and blue.

## Generate and vary

From the repository root, run Blender 4.3 with:

```sh
blender --background --python-exit-code 1 \
  --python assets/shrubs/bilberry/tools/build_bilberry.py

blender --background --python-exit-code 1 \
  --python assets/shrubs/bilberry/tools/build_bilberry.py -- --seed 27 --no-renders
```

Use `--random` to pick a new seed. Seeds change the shrub's width, height, lean, and stem arrangement. Variants go under `variants/` unless you pass `--output-dir`. The generator reuses the repository's material, export, and studio code from the [pine tools](../../conifers/pine/tools).

For wind, the GLB uses the vertex attributes expected by the [shared Vulkan shader](../../conifers/pine/tools/pine_wind.vert.spv). Pass the model's local height and use the leaf alpha cutoff in the shadow and depth passes.

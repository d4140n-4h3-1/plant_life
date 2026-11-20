# Norway spruce

A narrow-crowned *Picea abies* with upswept branch tips, hanging needle-covered branchlets, and long cones. The reference mesh is 11.40 m tall and uses 10,249 triangles. Its origin is at ground level.

| File | Contents |
| --- | --- |
| [norway-spruce.glb](norway-spruce.glb) | Y-up game mesh in meters with three materials and embedded textures |
| [norway-spruce.blend](norway-spruce.blend) | Z-up editable model with packed textures |
| [textures](textures) | 512 × 512 base color, tangent-space normal, ORM, and height maps for bark, needles, and cones |
| [source](source) | Generated spruce bark swatch and provenance |
| [Full tree](renders/spruce-full.png) | Crown silhouette and lower limbs |
| [Detail](renders/spruce-detail.png) | Hanging branchlets, short needles, and cones |
| [Seeded examples](renders/spruce-variants.png) | Seed 2, the reference tree, and seed 11 from left to right |
| [Wind GIF](renders/spruce-wind.gif) | A 2.4-second loop of the spruce in a gust |

The mesh has one UV set. The needle material is double-sided with a 0.40 alpha cutoff. Base color is sRGB. The normal and packed ORM maps use linear sampling. ORM channels contain occlusion, roughness, and metallic, respectively.

## Generate and render

Run these from the repository root with Blender 4.3.

```sh
blender --background --python-exit-code 1 \
  --python assets/conifers/norway-spruce/tools/build_spruce.py

blender --background --python-exit-code 1 \
  --python assets/conifers/norway-spruce/tools/build_spruce.py -- --seed 2 --no-renders

blender --background --python-exit-code 1 \
  --python assets/conifers/norway-spruce/tools/render_examples.py -- --seeds 2 11
```

Use `--random` in place of `--seed 2` to choose a new seed. Seeded models go into `variants/` by default, or you can pass `--output-dir`. Seeds vary height, crown breadth, lean, and branch layout. The spruce tools reuse the repository's conifer material, export, and studio code from [the pine tools](../pine/tools).

## Wind

The spruce GLB uses the same vertex inputs as the [Vulkan wind shader](../pine/tools/pine_wind.vert.spv). Pass the spruce's local height (11.40 m for the reference tree) and use the spruce material cutoff in foliage depth and shadow passes. To record a preview with Blender and ImageMagick 7, run:

```sh
blender --background assets/conifers/norway-spruce/norway-spruce.blend --python-exit-code 1 \
  --python assets/conifers/norway-spruce/tools/record_spruce_wind.py
```

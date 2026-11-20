# Forest loam

A tileable woodland soil material with granular earth and small fragments of dry leaf litter. The example mesh is 1 × 1 m with one UV repeat. Scale the UVs by surface dimensions in meters to keep the same texel scale on a larger terrain.

| File | Contents |
| --- | --- |
| [forest-loam.blend](forest-loam.blend) | One-meter tile with packed material textures |
| [forest-loam.glb](forest-loam.glb) | Y-up tile in meters with embedded PBR maps |
| [Textures](textures) | 1024 × 1024 base color, tangent-space normal, ORM, and height maps |
| [Soil preview](renders/forest-loam.png) | Multiple repeats under studio lighting |

The soil is generated procedurally. The normal map is tangent-space +Y. Normal, ORM, and height are linear data. The ORM channels are occlusion, roughness, and metallic. Sample all textures with repeat addressing and load the base color as sRGB.

## Build

From the repository root with Blender 4.3:

```sh
blender --background --python-exit-code 1 \
  --python assets/terrain/forest-loam/tools/build_forest_loam.py
```

Pass `-- --output-dir PATH --no-renders` to build the tile and maps in another folder.

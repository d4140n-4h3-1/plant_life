# Floating sweet-grass

*Glyceria fluitans*. Shallow, sheltered water beside streams. Long ribbon-shaped leaves arch outward near the surface.

- [Blender source](floating-sweet-grass.blend)
- [GLB with baked wind](floating-sweet-grass.glb)
- [Wind-rigged GLB](floating-sweet-grass-rigged.glb)
- [Texture maps](textures/)

## Build

Run the [Python builder](tools/build_floating_sweet_grass.py) in Blender 4.3, then
run `assets/tools/bake_plant_wind.py` and `assets/tools/rig_plant_wind.py`
on the exported GLB. Pass `-- --seed 27 --no-renders` to Blender for a
reproducible variant.

# Creeping bent

*Agrostis stolonifera*. Low, spreading grass for exposed wet soil immediately above the waterline.

- [Blender source](creeping-bent.blend)
- [GLB with baked wind](creeping-bent.glb)
- [Wind-rigged GLB](creeping-bent-rigged.glb)
- [Texture maps](textures/)

## Build

Run the [Python builder](tools/build_creeping_bent.py) in Blender 4.3, then
run `assets/tools/bake_plant_wind.py` and `assets/tools/rig_plant_wind.py`
on the exported GLB. Pass `-- --seed 27 --no-renders` to Blender for a
reproducible variant.

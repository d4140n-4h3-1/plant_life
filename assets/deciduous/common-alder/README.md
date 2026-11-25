# Common alder

*Alnus glutinosa*. An upright stream-bank tree with rounded, dark-green leaves and dark fissured bark. The reference mesh stands **13.35 m** tall and uses **5,660 triangles**, with a ground-level pivot.

- [Editable Blender model](common-alder.blend)
- [Y-up GLB with baked wind](common-alder.glb)
- [GLB with a wind rig](common-alder-rigged.glb)
- [512 × 512 texture maps](textures/)
- [Studio preview](renders/common-alder-full.png)

## Build

From the repository root, use Blender 4.3.

```sh
blender --background --python-exit-code 1 \
  --python assets/deciduous/common-alder/tools/build_common_alder.py
python3 assets/tools/bake_plant_wind.py assets/deciduous/common-alder/common-alder.glb
python3 assets/tools/rig_plant_wind.py assets/deciduous/common-alder/common-alder.glb
```

Use `-- --seed 27 --no-renders` for a reproducible geometry variant without rendering.

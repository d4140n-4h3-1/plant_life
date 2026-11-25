# White willow

*Salix alba*. A spreading stream-bank tree with narrow, pale-green leaves on drooping outer twigs. The reference mesh stands **11.60 m** tall and uses **5,660 triangles**, with a ground-level pivot.

- [Editable Blender model](white-willow.blend)
- [Y-up GLB with baked wind](white-willow.glb)
- [GLB with a wind rig](white-willow-rigged.glb)
- [512 × 512 texture maps](textures/)
- [Studio preview](renders/white-willow-full.png)

## Build

From the repository root, use Blender 4.3.

```sh
blender --background --python-exit-code 1 \
  --python assets/deciduous/white-willow/tools/build_white_willow.py
python3 assets/tools/bake_plant_wind.py assets/deciduous/white-willow/white-willow.glb
python3 assets/tools/rig_plant_wind.py assets/deciduous/white-willow/white-willow.glb
```

Use `-- --seed 27 --no-renders` for a reproducible geometry variant without rendering.

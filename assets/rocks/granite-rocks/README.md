# Granite rocks

A rounded cobble, low faceted slab, and tall irregular boulder. Each GLB is a separate Y-up mesh in meters with its own ground-level pivot and embedded granite textures. The Blender file groups the three editable meshes for side-by-side inspection.

| Mesh | Reference dimensions (m) | Triangles |
| --- | --- | ---: |
| [Cobble](granite-cobble.glb) | 0.33 × 0.25 × 0.18 | 80 |
| [Slab](granite-slab.glb) | 1.31 × 0.77 × 0.32 | 80 |
| [Boulder](granite-boulder.glb) | 0.90 × 0.72 × 0.95 | 320 |

The [shared 1024 × 1024 textures](textures) include base color, tangent-space normal, ORM, and height. See the [granite source swatch](source/) and the [rocks-on-loam render](renders/granite-on-loam.png).

## Build and vary

From the repository root with Blender 4.3:

```sh
blender --background --python-exit-code 1 \
  --python assets/rocks/granite-rocks/tools/build_granite_rocks.py

blender --background --python-exit-code 1 \
  --python assets/rocks/granite-rocks/tools/build_granite_rocks.py -- --seed 27 --no-renders
```

Each seed changes the individual dimensions, aspect ratios, angular offsets, and surface contours of all three rocks. Use `--random` to choose and print a new seed. Seeded versions go in `variants/` unless you set `--output-dir`.

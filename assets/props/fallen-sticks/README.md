# Fallen sticks

Four static woodland-floor props at real-world scale. Each has a pivot at soil
level and embeds its bark and leaf textures in the GLB.

| GLB | Length | Triangles |
| --- | ---: | ---: |
| [Bare twig](bare-twig.glb) | 0.52 m | 153 |
| [Bare fork](bare-fork.glb) | 0.92 m | 191 |
| [Leafy twig](leafy-twig.glb) | 0.63 m | 389 |
| [Leafy fork](leafy-fork.glb) | 1.20 m | 582 |

The leafy sticks carry curled, dry brown leaves made from double-sided
geometry. The [editable Blender scene](fallen-sticks.blend) lays the variants
out side by side. Individual GLBs export at the origin. Bark reuses the
repository's English oak swatch. The assets use the repository's CC0 license.

## Build

From the repository root, run Blender 4.3.

```sh
blender --background --python-exit-code 1 \
  --python assets/props/fallen-sticks/tools/build_fallen_sticks.py
```

## Generate a varied batch

```sh
blender --background --python-exit-code 1 \
  --python assets/props/fallen-sticks/tools/build_fallen_sticks.py -- \
  --seed 27 --count 12 --kind mixed
```

The builder varies length, thickness, curvature, fork angles and counts,
and the number, size, and curl of attached leaves. Use `--kind bare` or
`--kind leafy` for a single type. Mixed batches alternate the types for even
coverage. Use `--random` in place of `--seed` for a fresh batch and save the
printed seed to reproduce it. Each batch gets its own folder under
`variants/`. Use `--output-dir` to place it elsewhere.

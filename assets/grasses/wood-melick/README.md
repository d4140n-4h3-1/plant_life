# Wood melick

*Melica uniflora*. A woodland grass with gently bent, broad blades and nodding violet-brown spikelets. The reference plant is **0.52 m** tall and uses **955 triangles** with a ground-level pivot.

| File | Contents |
| --- | --- |
| [wood-melick.blend](wood-melick.blend) | Editable Blender model with packed textures |
| [wood-melick.glb](wood-melick.glb) | Y-up mesh in meters with embedded textures |
| [Textures](textures) | 512 × 512 base color, tangent-space normal, ORM, and height maps |
| [Full plant](renders/melick-full.png) | Overall shape |
| [Detail](renders/melick-detail.png) | Foliage and shoot detail |

One double-sided opaque material combines fresh blades, stems, and spikelets in a three-band atlas. The mesh uses one UV set. The GLB supplies the vertex attributes for the collection's [Vulkan wind shader](../../conifers/pine/tools/pine_wind.vert.spv). Pass the selected plant's local height and a distinct phase per instance.

## Build

Use Blender 4.3 from the repository root.

```sh
blender --background --python-exit-code 1 \
  --python assets/grasses/wood-melick/tools/build_wood_melick.py

blender --background --python-exit-code 1 \
  --python assets/grasses/wood-melick/tools/build_wood_melick.py -- --seed 27 --no-renders
```

Use `--random` to choose a new seed and `--output-dir PATH` to choose a destination. Otherwise, seeded outputs go into `variants/`. Variants change size, spread, and shoot arrangement.

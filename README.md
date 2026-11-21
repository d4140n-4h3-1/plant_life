# plant_life

A series of plant models.

## Conifers

Keep each tree in its own folder under `assets/conifers/`. Its Blender and GLB files sit alongside `textures/`, `source/`, `renders/`, and `tools/`.

### Norway spruce

A narrow conifer with hanging branchlets and elongated cones. See the model, maps, seeded examples, and tools in the [Norway spruce folder](assets/conifers/norway-spruce/README.md).

### Silver fir

A layered evergreen with flat needle sprays and upright cones. See the [silver fir models, textures, and generator](assets/conifers/silver-fir/README.md).

### European larch

An airy deciduous conifer in summer foliage, with needles clustered on spur shoots. See the [European larch models, textures, and generator](assets/conifers/european-larch/README.md).

### Pine

A pine with an irregular crown, curved branches with tapered lateral twigs, fine needle silhouettes, and a curved trunk with five root buttresses. The mesh is 7.2 m tall, uses 7,895 triangles, and has its origin at the base of the trunk for ground placement. One opaque material covers the bark. A double-sided, alpha-masked material covers the crossed foliage cards.

| File | Use |
| --- | --- |
| [pine.glb](assets/conifers/pine/pine.glb) | glTF 2.0 game import with embedded PBR textures, UVs, normals, and tangents |
| [pine.blend](assets/conifers/pine/pine.blend) | Editable Blender source with packed textures and a Z-up scene |
| [textures](assets/conifers/pine/textures) | Separate 512 × 512 PNG maps for bark and needles |
| [Full render](assets/conifers/pine/renders/pine-full.png) | Full silhouette |
| [Detail render](assets/conifers/pine/renders/pine-detail.png) | Branches and lower foliage |
| [Bark close-up](assets/conifers/pine/renders/pine-bark.png) | Trunk texture and lower branch junctions |
| [Wind GIF](assets/conifers/pine/renders/pine-wind.gif) | Loop of the pine bending and the outer branches fluttering |

The trunk and branches share a tileable bark texture derived from a photorealistic, AI-generated Scots pine swatch. The builder reduces broad lighting in the base color and estimates the relief and surface response from the swatch. One UV set (`UVMap` in Blender and `TEXCOORD_0` in glTF) wraps the trunk and branches and tiles the bark along their length. The foliage cards intentionally overlap in UV space to reuse the needle texture. Base color uses sRGB. The needle base color includes a linear alpha mask with a cutoff of 0.40, as configured in the GLB. Read the other maps as linear data. Normal maps are tangent-space with +Y (OpenGL) convention. The ORM map stores ambient occlusion in red, roughness in green, and metallic in blue. Height maps are optional source textures supplied separately.

The GLB uses glTF's meter scale and Y-up convention. The asset includes a single static mesh. Studio lighting and ground are used only for the renders.

## Rebuild

```sh
blender --background --python-exit-code 1 --python assets/conifers/pine/tools/build_pine.py
```

The generator uses Blender 4.3 and its bundled NumPy. Geometry and needle textures are generated locally from fixed seeds. The bark maps are generated from the [included swatch and its provenance](assets/conifers/pine/source).

### Generate variants

Pass an integer seed after Blender's `--` separator. The same seed reproduces the same geometry. Different seeds vary the height, crown width and taper, trunk lean, and branch layout. Variants keep the ground-level pivot, meter scale, and two game materials.

```sh
blender --background --python-exit-code 1 --python assets/conifers/pine/tools/build_pine.py -- --seed 27 --no-renders
```

This writes `pine.blend`, `pine.glb`, and the texture maps to `assets/conifers/pine/variants/pine-27/`. Set `--output-dir PATH` to choose a different folder. Omit `--no-renders` to include studio previews. Use `--random` in place of `--seed 27` to choose and print a new seed. Run without either flag to rebuild the reference pine.


### Wind

Use [`pine_wind.glsl`](assets/conifers/pine/tools/pine_wind.glsl) in a vertex shader for the Y-up GLB. Add the returned offset to the local vertex position before transforming it into world space. Use the tree's local height (7.2 m for the reference pine), elapsed time in seconds, a local XZ vector pointing downwind, a strength, and a per-instance phase in radians. Strength `0` gives still air. Use the same deformation in any shadow and depth passes.

To record the Blender preview again, install ImageMagick 7 and run:

```sh
blender --background assets/conifers/pine/pine.blend --python-exit-code 1 \
  --python assets/conifers/pine/tools/record_wind.py
```

The recorder writes a 2.4-second GIF and accepts `-- --output PATH` to save it elsewhere.

#### Vulkan

Use [`pine_wind.vert.spv`](assets/conifers/pine/tools/pine_wind.vert.spv) as a Vulkan 1.0 vertex stage with entry point `main`. The shader keeps the GLB's UVs and deforms the world-space normal and tangent for normal mapping. Pair it with your bark and alpha-masked foliage fragment shaders. Use the same vertex deformation and foliage cutoff in shadow and depth passes.

| Vertex location | glTF attribute | Vulkan format |
| --- | --- | --- |
| 0 | `POSITION` | `VK_FORMAT_R32G32B32_SFLOAT` |
| 1 | `NORMAL` | `VK_FORMAT_R32G32B32_SFLOAT` |
| 2 | `TEXCOORD_0` | `VK_FORMAT_R32G32_SFLOAT` |
| 3 | `TANGENT` | `VK_FORMAT_R32G32B32A32_SFLOAT` |

Bind a 64-byte column-major view-projection matrix as a vertex-stage uniform buffer at set 0, binding 0. It should use your engine's Vulkan clip-space convention.

| Vertex-stage push constant | Byte offset | Contents |
| --- | ---: | --- |
| `model` | 0 | Column-major local-to-world matrix |
| `wind` | 64 | Local XZ direction, strength, time in seconds |
| `tree` | 80 | Local height, instance phase in radians, two reserved floats |

The push-constant range is 96 bytes. Vertex outputs at locations 0 through 3 are UV (`vec2`), world normal (`vec3`), world tangent with handedness (`vec4`), and world position (`vec3`). Use a model transform with nonzero scale.

To rebuild the SPIR-V with the Vulkan SDK's `glslc`, run:

```sh
cd assets/conifers/pine/tools
glslc --target-env=vulkan1.0 pine_wind.vert -o pine_wind.vert.spv
```

## Deciduous trees

### Silver birch

A pale-trunked tree with an airy broadleaf crown. See the [silver birch asset and generator](assets/deciduous/silver-birch/README.md).

### Rowan

A deciduous tree with pinnate foliage and red-orange berries. See the [rowan asset and generator](assets/deciduous/rowan/README.md).

### English oak

A broad deciduous crown on a thick trunk with spreading limbs. See the [English oak asset and generator](assets/deciduous/english-oak/README.md).

## Shrubs

### Bilberry

A compact forest-understory shrub with small, serrated leaves and blue fruit. See the [bilberry model, texture maps, renders, and generator](assets/shrubs/bilberry/README.md).

### Common heather

A low, flowering shrub with pink late-summer sprays. See the [common heather asset and generator](assets/shrubs/common-heather/README.md).

### Common broom

An upright shrub with yellow spring flowers. See the [common broom asset and generator](assets/shrubs/common-broom/README.md).

### Common hawthorn

A dense hedgerow shrub with red haws. See the [common hawthorn asset and generator](assets/shrubs/common-hawthorn/README.md).

### Wild roses

[Dog rose](assets/shrubs/dog-rose/README.md) has arching canes and pink flowers. [Burnet rose](assets/shrubs/burnet-rose/README.md) forms a low, spreading bush with creamy white flowers.

## Grasses

### Sheep fescue

A fine-bladed tuft with dry seed heads. See the [models, texture maps, generator, and scatter example](assets/grasses/sheep-fescue/README.md).

### Tufted hairgrass

A taller clump grass with airy bronze panicles. See the [tufted hairgrass asset and generator](assets/grasses/tufted-hairgrass/README.md).

### Wood melick

A woodland grass with broad blades and nodding spikelets. See the [wood melick asset and generator](assets/grasses/wood-melick/README.md).

### Meadow foxtail

A meadow grass with dense cylindrical seed heads. See the [meadow foxtail asset and generator](assets/grasses/meadow-foxtail/README.md).

## Ferns

[Hard fern](assets/ferns/hard-fern/README.md) forms a narrow-frond rosette for shade. [Bracken](assets/ferns/bracken/README.md) has larger, divided fronds for woodland edges and clearings.

## Wildflowers

[Foxglove](assets/wildflowers/foxglove/README.md) adds tall pink bell spikes. [Wood sorrel](assets/wildflowers/wood-sorrel/README.md) adds low heart-shaped foliage and white flowers. [Oxeye daisy](assets/wildflowers/oxeye-daisy/README.md) adds white petals around raised yellow centers.

[English bluebell](assets/wildflowers/english-bluebell/README.md) adds drooping violet-blue flower spikes. [Common poppy](assets/wildflowers/common-poppy/README.md) adds scarlet blooms with dark centers.

## Environments

### Woodland clearing

A winding trail bordered by pine, Norway spruce, bilberry, and sheep fescue. See the [Blender scene, GLB, rendered views, and rebuild instructions](environments/woodland-clearing/README.md).

### Granite woodland

A loam trail winding through rock outcrops and a mixed canopy, with ferns and wildflowers along the banks. See the [Blender scene, GLB, and rendered views](environments/granite-woodland/README.md).

## Ground and rocks

[Forest loam](assets/terrain/forest-loam/README.md) is a one-meter tiling soil material. [Granite rocks](assets/rocks/granite-rocks/README.md) supplies a cobble, slab, and boulder with seeded geometry and size variation.

## Props

[Hanging lantern](assets/props/hanging-lantern/README.md) includes an animated chain pivot, a warm point light, and a Blender lighting test scene.

[Player lantern](assets/props/player-lantern/README.md) includes a hand attachment, an animated hinge, and a PS1-style carry test in Blender.

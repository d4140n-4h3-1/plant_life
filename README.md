# plant_life

A series of plant models.

## Plant wind

Every standalone plant GLB includes a 12-second `Wind` clip. Play it on repeat in a glTF player or engine that supports morph target animation. The plants rest in their original pose when the clip is idle. For repeated instances, start the clip at different offsets to vary their timing.

The clip uses a damped spring response to gusts, with a fixed downwind direction, anchored bases, and faster motion around the outer foliage. Branches, canes, fronds, flower stalks, and individual grass blades and seed stalks sway and rebound independently while following the motion at their attachment. The bake infers these attachments from the mesh geometry. Trees bend less than shrubs, ferns, grasses, and wildflowers. The wind is baked into the individual GLBs. The environment GLBs and Blender authoring files remain static.

| Plant group | Wind GIFs |
| --- | --- |
| Conifers | [European larch](assets/conifers/european-larch/renders/wind-preview.gif), [Norway spruce](assets/conifers/norway-spruce/renders/wind-preview.gif), [Pine](assets/conifers/pine/renders/wind-preview.gif), [Silver fir](assets/conifers/silver-fir/renders/wind-preview.gif) |
| Deciduous | [English oak](assets/deciduous/english-oak/renders/wind-preview.gif), [Rowan](assets/deciduous/rowan/renders/wind-preview.gif), [Silver birch](assets/deciduous/silver-birch/renders/wind-preview.gif) |
| Shrubs | [Bilberry](assets/shrubs/bilberry/renders/wind-preview.gif), [Burnet rose](assets/shrubs/burnet-rose/renders/wind-preview.gif), [Common broom](assets/shrubs/common-broom/renders/wind-preview.gif), [Common hawthorn](assets/shrubs/common-hawthorn/renders/wind-preview.gif), [Common heather](assets/shrubs/common-heather/renders/wind-preview.gif), [Dog rose](assets/shrubs/dog-rose/renders/wind-preview.gif) |
| Grasses | [Meadow foxtail](assets/grasses/meadow-foxtail/renders/wind-preview.gif), [Sheep fescue](assets/grasses/sheep-fescue/renders/wind-preview.gif), [Tufted hairgrass](assets/grasses/tufted-hairgrass/renders/wind-preview.gif), [Wood melick](assets/grasses/wood-melick/renders/wind-preview.gif) |
| Ferns | [Bracken](assets/ferns/bracken/renders/wind-preview.gif), [Hard fern](assets/ferns/hard-fern/renders/wind-preview.gif) |
| Wildflowers | [Common poppy](assets/wildflowers/common-poppy/renders/wind-preview.gif), [English bluebell](assets/wildflowers/english-bluebell/renders/wind-preview.gif), [Foxglove](assets/wildflowers/foxglove/renders/wind-preview.gif), [Oxeye daisy](assets/wildflowers/oxeye-daisy/renders/wind-preview.gif), [Wood sorrel](assets/wildflowers/wood-sorrel/renders/wind-preview.gif) |

After rebuilding a plant GLB, bake the clip again with Python, NumPy, and SciPy. Pass individual GLB paths to limit the bake to those files.

```sh
python assets/tools/bake_plant_wind.py
```

### Directional wind rigs

Every standalone plant has a companion `<plant>-rigged.glb` beside its baked GLB. The rigs start in the rest pose and expose two bend joints per limb. Tree trunks flex progressively more toward the crown, and branches inherit motion at their attachment height. Grass seed heads follow their stalks. The [rig files](assets/) can be posed in Blender or driven at runtime.

The directional previews use the runtime rig and show wind blowing right, reversing left, and dropping to calm.

[Meadow foxtail](assets/grasses/meadow-foxtail/renders/directional-wind.gif) · [Sheep fescue](assets/grasses/sheep-fescue/renders/directional-wind.gif) · [Tufted hairgrass](assets/grasses/tufted-hairgrass/renders/directional-wind.gif) · [Wood melick](assets/grasses/wood-melick/renders/directional-wind.gif) · [Pine](assets/conifers/pine/renders/directional-wind.gif) · [Bracken](assets/ferns/bracken/renders/directional-wind.gif)

Cycles previews of the same wind reversal are available for [pine](assets/conifers/pine/renders/directional-wind-cycles.gif) and [wood melick](assets/grasses/wood-melick/renders/directional-wind-cycles.gif).

With Three.js, load the rigged GLB using `GLTFLoader`, then add its scene to your scene and update its controller each frame. Pass a plant-local XZ vector pointing downwind. Its length controls strength, from zero for calm air to one for the reference wind. A wind change accelerates the limbs toward the new direction, and setting the vector to zero lets them settle.

```js
import { PlantWind } from "./assets/tools/plant_wind.mjs";

const { scene: plant } = await loader.loadAsync(
    "./assets/grasses/wood-melick/wood-melick-rigged.glb"
);
scene.add(plant);
const wind = new PlantWind(plant);

// In the render loop, with elapsed time since the last frame in seconds.
wind.update(deltaSeconds, localWindX, localWindZ);
```

If your wind input is in world space, rotate it into the rig's local space before passing its X and Z components. Create one controller per plant instance, and use `SkeletonUtils.clone` when duplicating a Three.js rig. The optional second constructor argument offsets gust timing in seconds. The existing GIFs show the fixed-direction baked clips.

Rebuild the rigs from the source GLBs with Python, NumPy, and SciPy. Pass individual source GLB paths to rebuild only those plants.

```sh
python assets/tools/rig_plant_wind.py
```

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

The GLB uses glTF's meter scale and Y-up convention. The asset includes a single mesh with the catalog’s baked wind clip. Studio lighting and ground are used only for the renders.

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

For live control of pine wind, stop the baked clip before applying the shader. Use [`pine_wind.glsl`](assets/conifers/pine/tools/pine_wind.glsl) in a vertex shader for the Y-up GLB. Add the returned offset to the local vertex position before transforming it into world space. Use the tree's local height (7.2 m for the reference pine), elapsed time in seconds, a local XZ vector pointing downwind, a strength, and a per-instance phase in radians. Strength `0` gives still air. Use the same deformation in any shadow and depth passes.

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

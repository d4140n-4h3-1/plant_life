# Low-poly trees

## Conifers

Keep each tree in its own folder under `assets/conifers/`. Its Blender and GLB files sit alongside `textures/`, `source/`, `renders/`, and `tools/`.

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

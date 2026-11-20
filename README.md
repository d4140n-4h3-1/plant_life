# Low-poly trees

## Pine

A pine with an irregular crown, tapered woody branches, and fine needle silhouettes. The mesh is 7.2 m tall, uses 4,524 triangles, and has its origin at the base of the trunk for ground placement. One opaque material covers the bark. A double-sided, alpha-masked material covers the crossed foliage cards.

| File | Use |
| --- | --- |
| [pine.glb](assets/pine/pine.glb) | glTF 2.0 game import with embedded PBR textures, UVs, normals, and tangents |
| [pine.blend](assets/pine/pine.blend) | Editable Blender source with packed textures and a Z-up scene |
| [textures](assets/pine/textures) | Separate 512 × 512 PNG maps for bark and needles |
| [Full render](renders/pine-full.png) | Full silhouette |
| [Detail render](renders/pine-detail.png) | Branches and lower foliage |
| [Bark close-up](renders/pine-bark.png) | Trunk texture and lower branch junctions |

The trunk and branches share a tileable bark texture derived from a photorealistic, AI-generated Scots pine swatch. The builder reduces broad lighting in the base color and estimates the relief and surface response from the swatch. Branch UVs follow the length of the wood. Base color uses sRGB. The needle base color includes a linear alpha mask with a cutoff of 0.40, as configured in the GLB. Read the other maps as linear data. Normal maps are tangent-space with +Y (OpenGL) convention. The ORM map stores ambient occlusion in red, roughness in green, and metallic in blue. Height maps are optional source textures supplied separately.

The GLB uses glTF's meter scale and Y-up convention. The asset includes a single static mesh. Studio lighting and ground are used only for the renders.

## Rebuild

```sh
blender --background --python-exit-code 1 --python tools/build_pine.py
```

The generator uses Blender 4.3 and its bundled NumPy. Geometry and needle textures are generated locally from fixed seeds. The bark maps are generated from the [included swatch and its provenance](assets/pine/source).

# Low-poly trees

## Pine

A stylized evergreen with a tiered, faceted crown and a flared trunk. The pine is 7.2 m tall, uses 746 triangles, and has its origin at the base of the trunk for ground placement. Its two opaque material slots are bark and needles.

| File | Use |
| --- | --- |
| [pine.glb](assets/pine/pine.glb) | glTF 2.0 game import with embedded PBR textures, UVs, normals, and tangents |
| [pine.blend](assets/pine/pine.blend) | Editable Blender source with packed textures and a Z-up scene |
| [textures](assets/pine/textures) | Separate 512 × 512 PNG maps for bark and needles |
| [Full render](renders/pine-full.png) | Full silhouette |
| [Detail render](renders/pine-detail.png) | Bark and lower foliage |

Base color uses sRGB. Read the other maps as linear data. Normal maps are tangent-space with +Y (OpenGL) convention. The ORM map stores ambient occlusion in red, roughness in green, and metallic in blue. Height maps are optional source textures supplied separately.

The GLB uses glTF's meter scale and Y-up convention. The asset includes a single static mesh. Studio lighting and ground are used only for the renders.

## Rebuild

```sh
blender --background --python-exit-code 1 --python tools/build_pine.py
```

The generator uses Blender 4.3 and its bundled NumPy. Geometry and texture maps are generated locally from fixed seeds.

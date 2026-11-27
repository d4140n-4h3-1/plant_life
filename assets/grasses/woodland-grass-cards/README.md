# Woodland grass cards

Low-growing ground cover for woodland soil and stream margins. Each standalone
GLB contains one clump on three crossed planes, for six triangles total. The
pivot is centered at soil level. The models use meters and glTF's Y-up axis.

| GLB | Card width × height | Placement |
| --- | --- | --- |
| [Carpet](woodland-grass-carpet.glb) | 0.64 × 0.20 m | Main cover in clearings and at trail edges |
| [Fescue](woodland-grass-fescue.glb) | 0.51 × 0.29 m | Fine tufts mixed through the carpet |
| [Bank](woodland-grass-bank.glb) | 0.72 × 0.38 m | Taller patches along damp banks |

The GLBs embed one 512 × 256 RGBA base-color texture per variant. Materials
use double-sided alpha masking with a 0.4 cutoff. Enable two-sided drawing in
the engine's material override if the importer drops that glTF setting.

To cover soil, scatter instances across the ground using the carpet as the
most frequent variant. Start with centers approximately 0.25–0.35 m apart,
then vary rotation, scale, and spacing. Seat the bases just below the surface
on slopes and use placement masks for trails, water, and exposed rock. For large
tracts, batch by variant and tune density and draw distance on the target GPU.

The [editable Blender scene](woodland-grass-cards.blend) displays the clumps
side by side. Each individual GLB exports at the origin and includes a 12-second
looping `Wind` clip. Morph targets move the card tops and keep the bases fixed.
When playing the clip on scattered instances, use different start offsets to
avoid synchronized motion. The Blender authoring scene holds the undeformed
cards. These assets use the repository's CC0 license.

## Build

From the repository root, run Blender 4.3.

```sh
blender --background --python-exit-code 1 \
  --python assets/grasses/woodland-grass-cards/tools/build_grass_cards.py
```

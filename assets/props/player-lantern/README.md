# Player lantern

An 896-triangle handheld oil lantern with a brass grip, dark steel bail, and a squat copper body. It is approximately 41 cm tall from grip to base. The Blender carry test uses a flat-shaded PS1-style traveler with a modeled face and a hand posed around the grip. The portable prop uses material colors and emissive flame geometry.

| File | Contents |
| --- | --- |
| [player-lantern.blend](player-lantern.blend) | Editable prop, looping player walk, and dusk lighting test |
| [player-lantern.glb](player-lantern.glb) | Handheld prop with attachment nodes, two-second sway, and a warm point light |
| [player-lantern-walk.glb](player-lantern-walk.glb) | Player and handheld lantern with a synchronized two-second walk clip |
| [Walk GIF](renders/lantern-walk.gif) | In-place walk and moving light in the Blender test stage |
| [Carry test](renders/carry-test.png) | Player proxy holding the lit lantern |
| [Grip detail](renders/grip-detail.png) | Close view of the handle, hand, and lamp |

## Attach to a player

Parent `HandGrip` to the hand bone or socket and reset its local position and rotation. The model origin is at the center of the horizontal grip. The grip runs along +X, and the lantern hangs below it along −Y in the exported glTF. Align the hand socket with those axes.

`LanternHinge` controls the body beneath the handle. Loop **Carry Sway** for a motion test, or drive the hinge from your character's movement. **Carry Flame** moves with the body. Its Blender default is an 8 W warm point light. In a Vulkan renderer, read its color and intensity from `KHR_lights_punctual` and update the light from the animated world transform. Use the emissive meshes for the visible flame and alpha blending for the glass.

## Play the walk

Loop **Lantern Walk** in the combined GLB. The clip is in place and includes two strides at one second per stride. Move the player root along its facing direction (+Z in glTF, −Y in Blender) at approximately 0.83 m/s to match the supporting foot speed. The clip drives the rigid player parts and lantern hinge together. In Blender, play frames 0–47 at 24 fps. Frame 48 duplicates the start for export.

## Build

Use Blender 4.3 from the repository root. ImageMagick 7 encodes the walk GIF. The script shares modeling helpers with the hanging lantern generator.

```sh
blender --background --python-exit-code 1 \
  --python assets/props/player-lantern/tools/build_player_lantern.py
```

Pass `-- --no-renders` to build just the models, or `-- --output-dir PATH` to choose a destination.

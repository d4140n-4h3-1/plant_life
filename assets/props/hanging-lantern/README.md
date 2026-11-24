# Hanging lantern

A six-sided iron and bronze oil lantern with glass panes, an interlocked chain, and a warm point light. The suspension eye is at the model origin. The lamp and chain hang below it.

| File | Contents |
| --- | --- |
| [hanging-lantern.blend](hanging-lantern.blend) | Editable lantern, four-second swing loop, and a separate lighting test collection |
| [hanging-lantern.glb](hanging-lantern.glb) | Y-up model in meters with the animation and a `KHR_lights_punctual` point light |
| [Lighting render](renders/lantern-lighting.png) | Warm light falling on a neutral plaster wall |
| [Swing GIF](renders/lantern-swing.gif) | Loop of the chain, lamp, and moving light |

## Lighting and motion

Play **Lantern Swing** on a loop. In Blender, the action runs from frame 0 to 96 at 24 fps. The mount stays fixed while **Suspension pivot** rotates. The chain, lantern, flame, and light follow the pivot. For physics-driven motion, use that pivot as the attachment point and drive its rotation from your constraint.

Adjust **Lantern point light** to change intensity and color. The Blender default is a warm 16 W point light. Hide **Cool test fill** to isolate it. The test stage also has a wall, floor, support beam, and close camera. The GLB carries the lantern hierarchy, omitting the test stage.

Enable the light from `KHR_lights_punctual` in a GLB importer. A custom renderer can use the extension's linear RGB color and intensity in candela, and update the light position from the animated node each frame. The flame meshes also use emissive materials for the visible glow. Render the opaque frame in the shadow pass, and handle the panes as alpha-blended glass.

## Build

Use Blender 4.3 or later (tested with 5.2) from the repository root. ImageMagick 7 is required to encode the GIF.

```sh
blender --background --python-exit-code 1 \
  --python assets/props/hanging-lantern/tools/build_lantern.py
```

Pass `-- --no-renders` to export only the Blender and GLB models. Pass `-- --output-dir PATH` to choose a different folder.

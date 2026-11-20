"""Render a seamless wind loop from the open Blender pine model."""
import argparse
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import bpy
import numpy as np

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from build_pine import point_at, studio_camera

FRAME_COUNT = 24
FRAME_DELAY = 10  # GIF delay in centiseconds.


def wind_offset(rest, height, cycle, direction, strength):
    """Z-up equivalent of pineWindOffset in pine_wind.glsl."""
    across = np.array((-direction[1], direction[0]))
    rise = np.clip(rest[:, 2]/height, 0, 1)
    bend = np.maximum((rise-.08)/.92, 0)**2
    gust = .5 + .5*np.sin(cycle-.9)
    forward = .115*(.20 + .55*gust**2 + .20*np.sin(cycle-1.2*rise))
    lateral = .027*np.sin(cycle-1.4*rise+.4)
    radius = np.clip(np.linalg.norm(rest[:, :2], axis=1)/(.33*height), 0, 1)
    flutter = .014*radius*np.sin(3*cycle + 2*(rest[:, :2] @ across) + 4*rise)
    return strength*height*bend[:, None] * (
        forward[:, None]*direction + (lateral+flutter)[:, None]*across
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=TOOLS.parent/"renders/pine-wind.gif")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])

    tree = bpy.context.scene.objects.get("Pine")
    if tree is None or tree.type != "MESH":
        parser.error("Open pine.blend before running this script.")
    rest = np.empty((len(tree.data.vertices), 3), dtype=np.float32)
    tree.data.vertices.foreach_get("co", rest.reshape(-1))
    height = float(rest[:, 2].max())
    direction = np.array((1.0, .28))
    direction /= np.linalg.norm(direction)

    framing = max(height/7.2, tree.dimensions.x/5, tree.dimensions.y/5)
    scene, camera = studio_camera(framing)
    camera.location = (11*framing, -17*framing, 8.1*framing)
    point_at(camera, (.13*framing, 0, 3.53*framing))
    camera.data.ortho_scale = 8.55*framing
    scene.render.resolution_x = 342
    scene.render.resolution_y = 420
    scene.cycles.samples = 6
    scene.cycles.seed = 24
    scene.cycles.use_animated_seed = False

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="pine-wind-") as temp:
        frames = []
        for frame in range(FRAME_COUNT):
            positions = rest.copy()
            positions[:, :2] += wind_offset(rest, height, frame*2*np.pi/FRAME_COUNT,
                                             direction, 1.0)
            tree.data.vertices.foreach_set("co", positions.reshape(-1))
            tree.data.update()
            frame_path = Path(temp)/f"wind-{frame:02}.png"
            frames.append(str(frame_path))
            scene.render.filepath = str(frame_path)
            bpy.ops.render.render(write_still=True)

        preview = Path(temp)/"wind.gif"
        subprocess.run(["magick", "-delay", str(FRAME_DELAY), *frames,
                        "-loop", "0", "+dither", "-colors", "96", "-layers", "Optimize",
                        str(preview)], check=True)
        output.write_bytes(preview.read_bytes())


if __name__ == "__main__":
    main()

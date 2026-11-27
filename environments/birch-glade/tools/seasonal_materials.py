"""Bake the shared annual palette into Blender and glTF base-color textures."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import bpy
import numpy as np

ASSETS = Path(__file__).resolve().parents[3] / "assets"
sys.path[:0] = [str(ASSETS / "tools"), str(ASSETS / "conifers/pine/tools")]
from build_pine import write_png
from seasonal_foliage import NEUTRAL, foliage_tint, load_palette
from seasonal_growth import AUTUMN_AMOUNT, AUTUMN_COLOR, LEAF_FALL, PEAK_COLOR_DAY

SOURCE_IMAGE = "seasonal_source_image"


def apply_blender(materials, day):
    palette = load_palette()
    day = (day - 1) % palette["days_per_year"] + 1
    with TemporaryDirectory(prefix="seasonal-foliage-") as scratch:
        for material in materials:
            profile = material.get(AUTUMN_COLOR, material.name)
            if not material.use_nodes or profile not in palette["profiles"]:
                continue
            shader = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
            base = shader.inputs["Base Color"]
            if not base.is_linked or base.links[0].from_node.type != "TEX_IMAGE":
                continue
            texture = base.links[0].from_node
            source = texture.get(SOURCE_IMAGE, texture.image)
            if source is None:
                continue
            if AUTUMN_COLOR in material:
                peak = foliage_tint(palette, profile, PEAK_COLOR_DAY[profile])
                tint = tuple(1.0 + (gain - 1.0) * material[AUTUMN_AMOUNT] for gain in peak)
            elif profile in LEAF_FALL and day >= LEAF_FALL[profile][2] - 17:
                tint = NEUTRAL
            else:
                tint = foliage_tint(palette, profile, day)
            previous = texture.image
            if tint == NEUTRAL:
                texture.image = source
            else:
                width, height = source.size
                rgba = np.empty(width * height * 4, dtype=np.float32)
                space = source.colorspace_settings.name
                try:
                    source.colorspace_settings.name = "Non-Color"
                    source.pixels.foreach_get(rgba)
                finally:
                    source.colorspace_settings.name = space
                rgba = rgba.reshape(height, width, 4)[::-1]
                srgb = rgba[..., :3]
                linear = np.where(srgb <= .04045, srgb / 12.92, ((srgb+.055)/1.055)**2.4)
                linear = np.clip(linear * tint, 0, 1)
                srgb[:] = np.where(linear <= .0031308, linear*12.92, 1.055*linear**(1/2.4)-.055)
                path = Path(scratch) / f"{material.name}.png"
                write_png(path, rgba)
                image = bpy.data.images.load(str(path))
                image.colorspace_settings.name = "sRGB"
                image.pack()
                image.filepath = "//" + path.name
                texture[SOURCE_IMAGE] = source
                texture.image = image
            if previous != source and previous.users == 0:
                bpy.data.images.remove(previous)

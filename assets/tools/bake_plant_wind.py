"""Bake a seamless wind clip into a standalone, Y-up plant GLB."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import tempfile

import numpy as np

from plant_branches import HARMONICS, branch_fields, local_displacement


# Tip compliance (fraction of height), natural frequency (Hz), damping,
# and small-scale flutter amplitude (fraction of height).
PROFILES = {
    "conifers": (0.050, 0.65, 0.40, 0.004),
    "deciduous": (0.055, 0.70, 0.38, 0.007),
    "shrubs": (0.105, 1.05, 0.40, 0.009),
    "ferns": (0.155, 1.25, 0.35, 0.012),
    "grasses": (0.220, 1.55, 0.34, 0.013),
    "wildflowers": (0.150, 1.15, 0.32, 0.010),
}
CLIP = "Wind"
PERIOD = 12.0
DIRECTION = np.array([0.94, 0.0, np.sqrt(1.0 - 0.94**2)])
ACROSS = np.array([-DIRECTION[2], 0.0, DIRECTION[0]])
BASE_TARGETS = ["Downwind bend", "Crosswind bend", "Stem drop", "Flutter sine", "Flutter cosine"]
BRANCH_TARGETS = ["Limb sway cosine", "Limb sway sine", "Limb rebound cosine", "Limb rebound sine"]


def read_glb(path):
    with path.open("rb") as file:
        magic, version, size = struct.unpack("<4sII", file.read(12))
        json_size, json_type = struct.unpack("<I4s", file.read(8))
        document = json.loads(file.read(json_size))
        bin_size, bin_type = struct.unpack("<I4s", file.read(8))
        data = bytearray(file.read(bin_size))
    if (magic, version, json_type, bin_type) != (b"glTF", 2, b"JSON", b"BIN\0"):
        raise ValueError(f"{path}: expected a two-chunk GLB 2.0")
    if size != 28 + json_size + bin_size or len(data) != bin_size:
        raise ValueError(f"{path}: incomplete or unsupported GLB")
    return document, data


def vectors(document, data, index, width):
    accessor = document["accessors"][index]
    view = document["bufferViews"][accessor["bufferView"]]
    if (accessor["componentType"] != 5126 or "sparse" in accessor
            or view["buffer"] != 0):
        raise ValueError("Expected a dense FLOAT vertex attribute in the embedded buffer")
    return np.ndarray(
        (accessor["count"], width), dtype="<f4", buffer=data,
        offset=view.get("byteOffset", 0) + accessor.get("byteOffset", 0),
        strides=(view.get("byteStride", width * 4), 4),
    ).astype(np.float64)


def triangle_indices(document, data, primitive):
    accessor = document["accessors"][primitive["indices"]]
    view = document["bufferViews"][accessor["bufferView"]]
    index_types = {5121: "<u1", 5123: "<u2", 5125: "<u4"}
    if primitive.get("mode", 4) != 4 or "sparse" in accessor or view["buffer"] != 0:
        raise ValueError("Expected indexed triangles in the embedded buffer")
    return np.frombuffer(data, dtype=index_types[accessor["componentType"]],
                         count=accessor["count"],
                         offset=view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
                         ).reshape(-1, 3).astype(np.int64)


def remove_previous_bake(document, data, mesh, animation):
    """Remove the known legacy bake, whose accessors and data are a suffix."""
    primitives = mesh["primitives"]
    suffix = [target[attr] for primitive in primitives for target in primitive["targets"]
              for attr in ("POSITION", "NORMAL", "TANGENT")]
    sampler, = animation["samplers"]
    suffix.extend([sampler["input"], sampler["output"]])
    accessors = document["accessors"]
    views = document["bufferViews"]
    view_suffix = [accessors[index]["bufferView"] for index in suffix]
    if (document["animations"] != [animation]
            or suffix != list(range(suffix[0], len(accessors)))
            or view_suffix != list(range(view_suffix[0], len(views)))):
        raise ValueError("Existing wind data was modified and cannot be replaced automatically")
    start = views[view_suffix[0]]["byteOffset"]
    cursor = start
    for index in view_suffix:
        view = views[index]
        if view["buffer"] != 0 or view["byteOffset"] != cursor:
            raise ValueError("Expected contiguous wind data at the end of the buffer")
        cursor += view["byteLength"]
    if cursor != len(data):
        raise ValueError("Unexpected data after the existing wind bake")
    del data[start:]
    del accessors[suffix[0]:]
    del views[view_suffix[0]:]
    del document["animations"]
    del mesh["weights"]
    del mesh["extras"]["targetNames"]
    for primitive in primitives:
        del primitive["targets"]


def append_accessor(document, data, values, kind, bounds=False, component_type=5126, target=None):
    values = np.asarray(values, dtype={5126: "<f4", 5123: "<u2"}[component_type])
    views = document["bufferViews"]
    accessors = document["accessors"]
    accessor = dict(bufferView=len(views), componentType=component_type,
                    count=len(values), type=kind)
    if bounds:
        accessor.update(min=np.atleast_1d(values.min(axis=0)).tolist(),
                        max=np.atleast_1d(values.max(axis=0)).tolist())
    view = dict(buffer=0, byteOffset=len(data), byteLength=values.nbytes)
    if target is not None:
        view["target"] = target
    views.append(view)
    data.extend(values.tobytes())
    accessors.append(accessor)
    return len(accessors) - 1


def displacement(position, base, height, profile):
    """Spatial modes shared across materials and mesh seams."""
    compliance, _, _, flutter = profile
    relative = position / height
    rise = np.maximum((position[:, 1] - base) / height, 0.0)
    bend = rise**2
    # Approximate the vertical drop of a bending stem with a separate mode.
    drop = -(2.0 / 3.0) * height * compliance**2 * rise**3
    phase = 8.0 * (relative @ ACROSS) + 3.0 * rise + 4.0 * (relative @ DIRECTION)
    envelope = height * flutter * bend * np.minimum(1.0, 0.25 + 2.0 *
                                                   np.linalg.norm(relative[:, [0, 2]], axis=1))
    return np.stack((
        (height * compliance * bend)[:, None] * DIRECTION,
        (height * compliance * bend)[:, None] * ACROSS,
        drop[:, None] * np.array([0.0, 1.0, 0.0]),
        (envelope * np.sin(phase))[:, None] * ACROSS,
        (envelope * np.cos(phase))[:, None] * ACROSS,
    ))


def wind_weights(seconds, profile, seed):
    _, frequency, damping, _ = profile
    rng = np.random.default_rng(seed)
    omega = 2.0 * np.pi / PERIOD
    natural = 2.0 * np.pi * frequency

    def response(harmonics, amplitudes):
        angular = omega * np.asarray(harmonics)
        # Steady-state response of x'' + 2*zeta*w*x' + w²*x = w²*load.
        transfer = natural**2 / (natural**2 - angular**2 + 2j * damping * natural * angular)
        phases = rng.uniform(0.0, 2.0 * np.pi, len(angular))
        return np.real(np.exp(1j * (seconds[:, None] * angular + phases)) @
                       (np.asarray(amplitudes) * transfer))

    forward = 0.47 + response([1, 2, 4, 7], [0.21, 0.12, 0.07, 0.03])
    side = response([2, 3, 6], [0.13, 0.08, 0.03])
    flutter = 0.45 + 0.30 * forward
    carrier = omega * seconds * 19 + rng.uniform(0, 2 * np.pi)
    weights = np.column_stack((forward, side, forward**2 + side**2,
                               flutter * np.cos(carrier), flutter * np.sin(carrier)))
    carriers = omega * seconds[:, None] * HARMONICS
    envelope = 0.75 + 0.40 * forward
    branch = np.stack((np.cos(carriers), np.sin(carriers)), axis=-1)
    weights = np.column_stack((weights, envelope[:, None] * branch.reshape(len(seconds), -1)))
    weights[-1] = weights[0]
    return weights


def bake(path, category, *, whole_mesh=False):
    profile = PROFILES[category]
    document, data = read_glb(path)
    animations = document.get("animations", [])
    existing = next((animation for animation in animations if animation.get("name") == CLIP), None)
    if len(document["meshes"]) != 1 or len(document["nodes"]) != 1:
        raise ValueError(f"{path}: expected one untransformed mesh node")
    node = document["nodes"][0]
    if node.get("mesh") != 0 or node.keys() & {"matrix", "translation", "rotation", "scale", "skin"}:
        raise ValueError(f"{path}: expected one untransformed mesh node")
    mesh = document["meshes"][0]
    whole_mesh = whole_mesh or mesh.get("extras", {}).get("windWholeMesh", False)
    target_names = BASE_TARGETS if whole_mesh else BASE_TARGETS + BRANCH_TARGETS
    primitives = mesh["primitives"]
    if existing:
        names = mesh.get("extras", {}).get("targetNames")
        if names == target_names:
            return False
        if names != BASE_TARGETS:
            raise ValueError(f"{path}: existing Wind clip did not come from the catalog baker")
        remove_previous_bake(document, data, mesh, existing)
    if any("targets" in primitive for primitive in primitives):
        raise ValueError(f"{path}: existing morph targets require a separate integration")

    attributes = [primitive["attributes"] for primitive in primitives]
    positions = [vectors(document, data, attr["POSITION"], 3) for attr in attributes]
    bottom = min(position[:, 1].min() for position in positions)
    top = max(position[:, 1].max() for position in positions)
    base = max(0.0, bottom) + 0.025 * (top - max(0.0, bottom))
    height = top - base
    if height <= 0.0:
        raise ValueError(f"{path}: expected a plant extending above its ground pivot")

    seed = int.from_bytes(hashlib.sha256(path.stem.encode()).digest()[:4], "little")
    fields = None
    if not whole_mesh:
        triangles = [triangle_indices(document, data, primitive) for primitive in primitives]
        ribbon_uv = None
        if category == "grasses" and len(primitives) == 1:
            ribbon_uv = vectors(document, data, attributes[0]["TEXCOORD_0"], 2)
        fields = branch_fields(positions, triangles, base, height,
                               category in {"conifers", "deciduous"}, DIRECTION, ACROSS, seed,
                               PERIOD, ribbon_uv=ribbon_uv)

    for index, (primitive, attr, position) in enumerate(zip(primitives, attributes, positions)):
        def deform(points):
            offsets = displacement(points, base, height, profile)
            if fields is None:
                return offsets
            return np.concatenate((
                offsets,
                local_displacement(points, fields[0][index], fields, base, height),
            ))

        offsets = deform(position)
        step = height * 0.0001
        gradients = np.stack([
            (deform(position + axis) - deform(position - axis)) / (2 * step)
            for axis in np.eye(3) * step
        ], axis=-1)
        normal = vectors(document, data, attr["NORMAL"], 3)
        tangent = vectors(document, data, attr["TANGENT"], 4)[:, :3]
        targets = []
        for offset, gradient in zip(offsets, gradients):
            # Linearized inverse-transpose for normals and forward Jacobian for tangents.
            normal_delta = -np.einsum("nji,nj->ni", gradient, normal)
            normal_delta -= np.sum(normal_delta * normal, axis=1)[:, None] * normal
            tangent_delta = np.einsum("nij,nj->ni", gradient, tangent)
            tangent_delta -= np.sum(tangent_delta * tangent, axis=1)[:, None] * tangent
            targets.append({
                "POSITION": append_accessor(document, data, offset, "VEC3", bounds=True),
                "NORMAL": append_accessor(document, data, normal_delta, "VEC3"),
                "TANGENT": append_accessor(document, data, tangent_delta, "VEC3"),
            })
        primitive["targets"] = targets

    mesh["weights"] = [0.0] * len(targets)
    extras = mesh.setdefault("extras", {})
    extras["targetNames"] = target_names
    if whole_mesh:
        extras["windWholeMesh"] = True
    seconds = np.linspace(0, PERIOD, round(PERIOD * 30) + 1)
    keys = wind_weights(seconds, profile, seed)[:, :len(target_names)]
    document.setdefault("animations", []).append({
        "name": CLIP,
        "samplers": [{
            "input": append_accessor(document, data, seconds, "SCALAR", bounds=True),
            "output": append_accessor(document, data, keys.reshape(-1), "SCALAR"),
            "interpolation": "LINEAR",
        }],
        "channels": [{"sampler": 0, "target": {"node": 0, "path": "weights"}}],
    })
    write_glb(path, document, data)
    return True


def write_glb(path, document, data):
    document["buffers"][0]["byteLength"] = len(data)
    metadata = json.dumps(document, separators=(",", ":")).encode()
    metadata += b" " * (-len(metadata) % 4)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        try:
            file.write(struct.pack("<4sIII4s", b"glTF", 2, 28 + len(metadata) + len(data),
                                   len(metadata), b"JSON"))
            file.write(metadata)
            file.write(struct.pack("<I4s", len(data), b"BIN\0"))
            file.write(data)
            file.close()
            temporary.chmod(path.stat().st_mode & 0o777 if path.exists() else 0o644)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path,
                        help="GLBs under a supported plant category; defaults to the catalog")
    args = parser.parse_args()
    assets = Path(__file__).resolve().parents[1]
    paths = args.files or sorted(
        path for category in PROFILES for path in (assets / category).glob("*/*.glb")
        if not path.stem.endswith("-rigged")
    )
    for path in paths:
        category = next((part for part in reversed(path.parts[:-1]) if part in PROFILES), None)
        if category is None:
            parser.error(f"{path}: no supported plant category in path")
        result = "baked" if bake(path, category) else "already baked"
        print(f"{path.name}: {result}")


if __name__ == "__main__":
    main()

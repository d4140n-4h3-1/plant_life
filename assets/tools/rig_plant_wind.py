"""Build directional wind rigs from the standalone plant GLBs."""
import argparse
import hashlib
from pathlib import Path

import numpy as np

from bake_plant_wind import (
    ACROSS, CLIP, DIRECTION, PERIOD, PROFILES, append_accessor, branch_fields,
    read_glb, remove_previous_bake, triangle_indices, vectors, write_glb,
)


def joint(nodes, name, translation, parent=None, wind=None):
    index = len(nodes)
    node = {"name": name, "translation": translation.tolist()}
    if wind is not None:
        node["extras"] = {"plantWind": wind}
    nodes.append(node)
    if parent is not None:
        nodes[parent].setdefault("children", []).append(index)
    return index


def smoothstep(edge0, edge1, values):
    progress = np.clip((values - edge0) / (edge1 - edge0), 0, 1)
    return progress**2 * (3 - 2 * progress)


def repair_degenerate_tangents(document, data, attrs):
    index = attrs["TANGENT"]
    tangent = vectors(document, data, index, 4)
    zero = np.linalg.norm(tangent[:, :3], axis=1) < 1e-8
    if not zero.any():
        return
    normals = vectors(document, data, attrs["NORMAL"], 3)[zero]
    reference = np.eye(3)[np.argmin(np.abs(normals), axis=1)]
    fallback = np.cross(reference, normals)
    fallback /= np.linalg.norm(fallback, axis=1)[:, None]
    accessor = document["accessors"][index]
    view = document["bufferViews"][accessor["bufferView"]]
    stored = np.ndarray(
        tangent.shape, dtype="<f4", buffer=data,
        offset=view.get("byteOffset", 0) + accessor.get("byteOffset", 0),
        strides=(view.get("byteStride", 16), 4),
    )
    stored[zero, :3] = fallback


def rig(source, category):
    document, data = read_glb(source)
    mesh, = document["meshes"]
    if mesh.get("extras", {}).get("windWholeMesh"):
        print(f"{source}: uses a whole-mesh Wind clip")
        return
    nodes = document["nodes"]
    original, = nodes
    if original.get("mesh") != 0 or original.keys() & {"matrix", "translation", "rotation", "scale", "skin"}:
        raise ValueError(f"{source}: expected one untransformed mesh node")
    animation = next((clip for clip in document.get("animations", []) if clip.get("name") == CLIP), None)
    if animation:
        remove_previous_bake(document, data, mesh, animation)
    if any("targets" in primitive for primitive in mesh["primitives"]):
        raise ValueError(f"{source}: existing morph targets require a separate integration")

    primitives = mesh["primitives"]
    positions = [vectors(document, data, p["attributes"]["POSITION"], 3) for p in primitives]
    triangles = [triangle_indices(document, data, p) for p in primitives]
    top = max(position[:, 1].max() for position in positions)
    ground = max(0.0, min(position[:, 1].min() for position in positions))
    base = ground + 0.025 * (top - ground)
    height = top - base
    if height <= 0:
        raise ValueError(f"{source}: expected a plant extending above its ground pivot")

    seed = int.from_bytes(hashlib.sha256(source.stem.encode()).digest()[:4], "little")
    ribbon_uv = None
    if category == "grasses" and len(primitives) == 1:
        ribbon_uv = vectors(document, data, primitives[0]["attributes"]["TEXCOORD_0"], 2)
    tree = category in {"conifers", "deciduous"}
    owners, roots, axes, lengths, hinges, _, coefficients = branch_fields(
        positions, triangles, base, height, tree, DIRECTION, ACROSS, seed, PERIOD,
        ribbon_uv=ribbon_uv,
    )

    origin = np.zeros(3)
    anchor = joint(nodes, "Wind Anchor", origin)
    joint_positions = [origin]
    supports = [anchor]
    compliance, frequency, damping, _ = PROFILES[category]
    if tree:
        # The tapered trunk concentrates flex in the thinner upper sections.
        for section, (rise, share) in enumerate(
            zip((0.04, 0.28, 0.53, 0.76), (0.04, 0.12, 0.29, 0.55)), start=1
        ):
            pivot = np.array([0.0, base + rise * height, 0.0])
            supports.append(joint(nodes, f"Wind Trunk {section}",
                                  pivot - joint_positions[-1], supports[-1], {
                "axis": [0, 1, 0], "gain": compliance * 0.90 * share,
                "frequency": frequency, "damping": damping, "flutter": [0, 0, 0, 0],
            }))
            joint_positions.append(pivot)

    support_levels = np.array([joint_positions[node - 1][1] for node in supports[1:]])
    transition = height * 0.055
    support_nodes = np.array(supports)

    def support_weights(y):
        upper = np.searchsorted(support_levels, y + transition)
        lower = np.maximum(upper - 1, 0)
        if not tree:
            return lower, upper, np.zeros_like(y)
        hinge_y = support_levels[lower]
        blend = smoothstep(np.maximum(base, hinge_y - transition), hinge_y + transition, y)
        return lower, upper, blend

    root_lower, root_upper, root_blend = support_weights(roots[:, 1])
    branch_supports = support_nodes[np.where(root_blend >= 0.5, root_upper, root_lower)]

    # Skin joint indices correspond to node indices minus one (the mesh node).
    branches = []
    median = np.median(lengths)
    for index, (root, axis, length, hinge, response) in enumerate(
        zip(roots, axes, lengths, hinges, coefficients)
    ):
        span = length - hinge
        pivot = root + axis * hinge
        middle = pivot + axis * (0.46 * span)
        stiffness = np.clip((median / length)**0.42, 0.72, 1.55)
        gain = (0.085 + compliance * 1.5) / stiffness
        motion = {
            "axis": axis.tolist(), "frequency": float(np.clip(frequency * stiffness * 1.35, 0.55, 3)),
            "damping": damping, "flutter": (response / length * 0.85).tolist(),
        }
        support = branch_supports[index]
        bottom_joint = joint(nodes, f"Wind Limb {index + 1}",
                             pivot - joint_positions[support - 1], int(support),
                             {**motion, "gain": float(gain * 0.72)})
        tip_joint = joint(nodes, f"Wind Tip {index + 1}", middle - pivot, bottom_joint,
                          {**motion, "gain": float(gain * 0.50),
                           "flutter": (response / length * 0.45).tolist()})
        branches.append((bottom_joint - 1, tip_joint - 1))
        joint_positions.extend([pivot, middle])

    branch_joints = np.array(branches)
    for primitive, position, assignment in zip(primitives, positions, owners):
        branch = np.maximum(assignment, 0)
        root_weight = smoothstep(base, base + height * 0.075, position[:, 1])
        projected = np.einsum("ij,ij->i", position - roots[branch], axes[branch])
        progress = (projected - hinges[branch]) / (lengths[branch] - hinges[branch])
        drive = smoothstep(0, 0.31, progress) * root_weight * (assignment >= 0)
        tip_weight = smoothstep(0.46, 0.93, progress) * drive
        support_y = np.where(assignment >= 0, roots[branch, 1], position[:, 1])
        lower, upper, blend = support_weights(support_y)
        # The fixed base stays pinned, even on ground-level limbs whose root is higher.
        blend *= root_weight * (upper != lower)
        indices = np.column_stack((support_nodes[lower] - 1, support_nodes[upper] - 1,
                                   branch_joints[branch]))
        weights = np.column_stack(((1 - drive) * (1 - blend), (1 - drive) * blend,
                                   drive - tip_weight, tip_weight))
        indices[weights == 0] = 0
        attrs = primitive["attributes"]
        repair_degenerate_tangents(document, data, attrs)
        attrs["JOINTS_0"] = append_accessor(
            document, data, indices, "VEC4", component_type=5123, target=34962
        )
        attrs["WEIGHTS_0"] = append_accessor(document, data, weights, "VEC4", target=34962)

    inverse_binds = np.repeat(np.eye(4)[None, :, :], len(joint_positions), axis=0)
    inverse_binds[:, 3, :3] = -np.array(joint_positions)  # Column-major glTF matrices.
    document["skins"] = [{
        "name": "Plant Wind", "skeleton": anchor, "joints": list(range(1, len(nodes))),
        "inverseBindMatrices": append_accessor(document, data, inverse_binds.reshape(-1, 16), "MAT4"),
    }]
    document["scenes"][document.get("scene", 0)]["nodes"].append(anchor)
    original["skin"] = 0
    output = source.with_stem(source.stem + "-rigged")
    write_glb(output, document, data)
    print(f"{output}: {len(branches)} articulated limbs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    paths = args.files or sorted(
        path for category in PROFILES for path in (root / category).glob("*/*.glb")
        if not path.stem.endswith("-rigged")
    )
    for path in paths:
        category = next((part for part in reversed(path.parts[:-1]) if part in PROFILES), None)
        if category is None or path.stem.endswith("-rigged"):
            parser.error(f"{path}: expected a standalone source plant GLB")
        rig(path, category)


if __name__ == "__main__":
    main()

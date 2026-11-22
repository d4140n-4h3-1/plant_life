"""Recover branch attachments from the procedural plant meshes."""
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def mesh_islands(position, triangles, height):
    # Weld same-position vertices split by glTF UV and normal seams.
    _, weld = np.unique(np.round(position / height, 6), axis=0, return_inverse=True)
    triangles = weld[triangles]
    edges = np.sort(np.concatenate([triangles[:, [0, 1]], triangles[:, [1, 2]],
                                    triangles[:, [2, 0]]]), axis=1)
    n = weld.max() + 1
    graph = coo_matrix((np.ones(len(edges)), edges.T), shape=(n, n)).tocsr()
    _, labels = connected_components(graph, directed=False)
    boundary, count = np.unique(edges, axis=0, return_counts=True)
    boundary = np.unique(boundary[count == 1])
    _, original = np.unique(weld, return_index=True)
    starts = np.isin(weld, boundary)
    groups = np.split(np.argsort(labels[weld], kind="stable"),
                      np.flatnonzero(np.diff(np.sort(labels[weld]))) + 1)
    return [(vertices, original[np.unique(weld[vertices[starts[vertices]]])])
            for vertices in groups]


def branch_geometry(position, islands, ribbon_uv=None):
    # The swept shoots have an open attachment ring and a capped tip.
    shoots = []
    for vertices, rim in islands:
        points = position[vertices]
        if ribbon_uv is not None:
            # Grass blades and seed sprays are open ribbons. Their V coordinate
            # is flipped in glTF, so it runs from 1 at the attachment to 0 at the tip.
            along = ribbon_uv[vertices, 1]
            ring = np.unique(points[along == along.max()], axis=0)
            root = ring.mean(axis=0)
            tip = points[along.argmin()]
        elif len(rim) < 3:
            # Closed stems have a ground cap. Recover its center from the lowest ring.
            unique = np.unique(points, axis=0)
            ground = unique[unique[:, 1] <= unique[:, 1].min() + 0.005 * np.ptp(unique[:, 1])]
            if len(ground) < 3:
                continue
            ring = ground
            root = ring.mean(axis=0)
        else:
            ring = np.unique(position[rim], axis=0)
            root = ring.mean(axis=0)
        if ribbon_uv is None:
            tip = points[np.argmax(np.linalg.norm(points - root, axis=1))]
        delta = tip - root
        length = np.linalg.norm(delta)
        if length > 0:
            axis = delta / length
            hinge = ((ring - root) @ axis).max()
            radius = np.linalg.norm(ring - root, axis=1).max()
            shoots.append((vertices, root, axis, length, radius, hinge))
    return shoots


HARMONICS = np.array([7, 13])


def branch_fields(positions, triangles, base, height, woody_tree, wind, across, seed, period, ribbon_uv=None):
    """Associate whole shoots and foliage islands with the supporting limb."""
    wood = positions[0]
    islands = mesh_islands(wood, triangles[0], height)
    shoots = branch_geometry(wood, islands, ribbon_uv)
    trunk = max(islands, key=lambda island: np.ptp(wood[island[0], 1]))[0]
    if woody_tree:
        trunk_points = np.unique(wood[trunk], axis=0)
        trunk_y = trunk_points[:, 1] / height
        # The trunk curves. Fit its centerline from the roughly symmetric rings.
        centerline = np.polynomial.polynomial.polyfit(trunk_y, trunk_points[:, [0, 2]], 4)

        def primary(shoot):
            vertices, root, _, length, radius, _ = shoot
            center = np.polynomial.polynomial.polyval(root[1] / height, centerline)
            return (vertices is not trunk and len(np.unique(wood[vertices], axis=0)) >= 10
                    and length > 0.035 * height and radius < 0.23 * length
                    and np.linalg.norm(root[[0, 2]] - center) < 0.047 * height)
    else:
        def primary(shoot):
            _, root, _, length, radius, _ = shoot
            return root[1] <= base + 0.055 * height and length > 0.10 * height and radius < 0.20 * length

    branches = [shoot for shoot in shoots if primary(shoot)]
    if not branches:
        raise ValueError("No primary branches or stems identified")
    owner = np.full(len(wood), -1, dtype=int)
    for index, (vertices, *_) in enumerate(branches):
        owner[vertices] = index

    roots = np.stack([root for _, root, *_ in branches])
    axes = np.stack([axis for _, _, axis, *_ in branches])
    lengths = np.array([length for _, _, _, length, *_ in branches])
    radii = np.array([radius for _, _, _, _, radius, _ in branches])
    hinges = np.array([hinge for _, _, _, _, _, hinge in branches])

    # Edges provide samples between the relatively sparse rings of each limb.
    edges = triangles[0][:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2)
    edges = np.unique(np.sort(edges, axis=1), axis=0)

    def support_tree(owners, include_trunk):
        selected = (owners >= 0) | include_trunk
        edges_selected = edges[selected[edges[:, 0]] & selected[edges[:, 1]]]
        starts, ends = wood[edges_selected].transpose(1, 0, 2)
        samples = np.concatenate([wood[selected], (starts + ends) / 2,
                                  (3*starts + ends) / 4, (starts + 3*ends) / 4])
        labels = np.concatenate([owners[selected], np.tile(owners[edges_selected[:, 0]], 3)])
        return cKDTree(samples), labels

    trunk_mask = np.zeros(len(wood), dtype=bool)
    if woody_tree:
        trunk_mask[trunk] = True
    tree, labels = support_tree(owner, trunk_mask)
    for vertices, root, *_ in shoots:
        if owner[vertices[0]] < 0 and not trunk_mask[vertices[0]]:
            owner[vertices] = labels[tree.query(root)[1]]

    tree, labels = support_tree(owner, trunk_mask)

    def foliage_owners(points, faces):
        assignment = np.full(len(points), -1, dtype=int)
        for vertices, _ in mesh_islands(points, faces, height):
            # The closest point on a card or organ tends to be its attachment.
            # Assign the whole piece so crossed cards and thin leaves keep their shape.
            distance, nearby = tree.query(points[vertices])
            assignment[vertices] = labels[nearby[distance.argmin()]]
        return assignment

    owners = [owner, *(foliage_owners(points, faces)
                      for points, faces in zip(positions[1:], triangles[1:]))]

    rng = np.random.default_rng(seed)
    relative_length = lengths / np.median(lengths)
    thickness = radii if ribbon_uv is None else np.maximum(radii, height * 0.0001)
    relative_thickness = thickness / np.median(thickness)
    natural = 2 * np.pi * np.clip(1.12 * relative_thickness**0.25 /
                                 relative_length**0.70, 0.55, 2.8)
    angular = 2 * np.pi * HARMONICS / period
    transfer = natural[:, None]**2 / (natural[:, None]**2 - angular**2 +
                                      0.72j * natural[:, None] * angular)
    phases = rng.uniform(-np.pi, np.pi, transfer.shape)
    response = transfer * np.exp(1j * phases) * [0.071, 0.027]
    # Wind acts across a limb. Upward turbulence gives horizontal limbs room to bounce.
    load = wind + np.array([0, 0.47, 0]) + 0.18 * across
    direction = load - (axes @ load)[:, None] * axes
    coefficients = np.stack((response.real, -response.imag), axis=-1).reshape(-1, 4)
    coefficients *= (lengths * np.clip(relative_thickness**-0.24, 0.65, 1.4))[:, None]
    return owners, roots, axes, lengths, hinges, direction, coefficients


def local_displacement(position, assignment, fields, base, height):
    _, roots, axes, lengths, hinges, direction, coefficients = fields
    branch = np.maximum(assignment, 0)
    distance = np.einsum("ij,ij->i", position - roots[branch], axes[branch])
    progress = np.clip((distance - hinges[branch]) /
                       (lengths[branch] - hinges[branch]), 0, 1.15)
    rooted = np.clip((position[:, 1] - base) / (0.07 * height), 0, 1)
    bend = progress**2 * (assignment >= 0) * rooted**2 * (3 - 2 * rooted)
    return np.einsum("im,i,ij->mij", coefficients[branch], bend, direction[branch])

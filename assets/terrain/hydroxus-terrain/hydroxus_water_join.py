"""Trim a tributary where it meets a receiving Hydroxus water surface."""
import bpy
from mathutils import Vector

EPSILON = 1.0e-6


def signed_area(a, b, point):
    return (b.x - a.x) * (point.y - a.y) - (b.y - a.y) * (point.x - a.x)


def split_polygon(polygon, a, b):
    """Split vertex records against the directed XY line from a to b."""
    positive, negative = [], []
    for start, end in zip(polygon, polygon[1:] + polygon[:1]):
        d0, d1 = signed_area(a, b, start[0]), signed_area(a, b, end[0])
        if d0 >= -EPSILON:
            positive.append(start)
        if d0 <= EPSILON:
            negative.append(start)
        if (d0 > EPSILON and d1 < -EPSILON) or (d1 > EPSILON and d0 < -EPSILON):
            fraction = d0 / (d0 - d1)
            crossing = tuple(left.lerp(right, fraction) for left, right in zip(start, end))
            positive.append(crossing)
            negative.append(crossing)
    return positive, negative


def subtract_triangle(polygon, triangle):
    """Return convex pieces outside the triangle."""
    if signed_area(*triangle) < 0:
        triangle = triangle[::-1]
    pieces = []
    for a, b in zip(triangle, triangle[1:] + triangle[:1]):
        polygon, outside = split_polygon(polygon, a, b)
        if len(outside) >= 3:
            pieces.append(outside)
        if len(polygon) < 3:
            break
    return pieces


def bounds(points):
    return (min(p.x for p in points), min(p.y for p in points),
            max(p.x for p in points), max(p.y for p in points))


def join_water_channels(tributary, receiving, blend_distance=0.65):
    """Remove overlapping surface and match height at the seam, preserving FlowUV."""
    if blend_distance <= 0:
        raise ValueError("The blend distance must be positive")
    bpy.context.view_layer.update()
    source = tributary.data
    flow_uv = source.uv_layers["FlowUV"]
    flow = source.attributes.get("flow_direction")
    source.calc_loop_triangles()
    receiver_mesh = receiving.data
    receiver_mesh.calc_loop_triangles()
    transform = receiving.matrix_world
    receiver_triangles = []
    for tri in receiver_mesh.loop_triangles:
        points = [transform @ receiver_mesh.vertices[i].co for i in tri.vertices]
        if abs(signed_area(*points)) > EPSILON:
            receiver_triangles.append((bounds(points), points))

    edge_counts = {}
    for face in receiver_mesh.polygons:
        for key in face.edge_keys:
            edge_counts[key] = edge_counts.get(key, 0) + 1
    banks = [(transform @ receiver_mesh.vertices[a].co, transform @ receiver_mesh.vertices[b].co)
             for (a, b), count in edge_counts.items() if count == 1]

    seam = []

    def conform(point):
        nearest = None
        distance = blend_distance
        for a, b in banks:
            along = b.xy - a.xy
            if along.length_squared <= EPSILON:
                continue
            t = min(1.0, max(0.0, (point.xy - a.xy).dot(along) / along.length_squared))
            candidate = a.lerp(b, t)
            separation = (point.xy - candidate.xy).length
            if separation < distance:
                nearest, distance = candidate, separation
        result = point.copy()
        if nearest is not None:
            weight = 1.0 - distance / blend_distance
            result.z += (nearest.z - result.z) * weight * weight * (3.0 - 2.0 * weight)
        if distance <= 2.0e-5:
            seam.append(result)
        return result

    vertices, texcoords, directions, faces = [], [], [], []
    vertex_indices = {}
    transform = tributary.matrix_world
    inverse = transform.inverted()
    for triangle in source.loop_triangles:
        polygon = [
            (transform @ source.vertices[source.loops[li].vertex_index].co,
             flow_uv.data[li].uv.copy(),
             (flow.data[source.loops[li].vertex_index].vector.copy() if flow else Vector((0, 0, 0))))
            for li in triangle.loops
        ]
        left, bottom, right, top = bounds([record[0] for record in polygon])
        pieces = [polygon]
        for (west, south, east, north), receiver in receiver_triangles:
            if left > east or right < west or bottom > north or top < south:
                continue
            pieces = [part for piece in pieces for part in subtract_triangle(piece, receiver)]
            if not pieces:
                break
        for piece in pieces:
            first = piece[0][0]
            for a, b in zip(piece[1:-1], piece[2:]):
                if abs(signed_area(first, a[0], b[0])) <= EPSILON:
                    continue
                face = []
                for point, uv, direction in (piece[0], a, b):
                    key = tuple(round(value, 6) for value in (*point.xy, *uv))
                    if key not in vertex_indices:
                        vertex_indices[key] = len(vertices)
                        vertices.append(inverse @ conform(point))
                        texcoords.append(uv)
                        directions.append(direction)
                    face.append(vertex_indices[key])
                if len(set(face)) == 3:
                    faces.append(face)

    if not faces:
        raise ValueError("The receiving surface covers the entire tributary")

    if len(seam) < 2:
        raise ValueError("The tributary must intersect the receiving bank")

    joined = bpy.data.meshes.new(f"{source.name} joined")
    joined.from_pydata(vertices, [], faces)
    joined.update()
    for material in source.materials:
        joined.materials.append(material)
    joined_uv = joined.uv_layers.new(name="FlowUV")
    for face in joined.polygons:
        face.use_smooth = True
        for li in face.loop_indices:
            joined_uv.data[li].uv = texcoords[joined.loops[li].vertex_index]
    if flow:
        joined_flow = joined.attributes.new("flow_direction", "FLOAT_VECTOR", "POINT")
        for index, direction in enumerate(directions):
            joined_flow.data[index].vector = direction
    tributary.data = joined
    if not source.users:
        bpy.data.meshes.remove(source)
    center = sum(seam, Vector((0, 0, 0))) / len(seam)
    tributary["join_center_local"] = tuple(inverse @ center)
    return center

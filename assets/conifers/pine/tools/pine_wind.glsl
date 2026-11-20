// Object-space wind displacement for the Y-up pine GLB.
// height is the tree height in local units. windDirection is an XZ vector
// pointing downwind. phase is a per-instance offset in radians.
vec3 pineWindOffset(vec3 position, float height, float seconds,
                    vec2 windDirection, float strength, float phase) {
    float directionLength = length(windDirection);
    if (height <= 0.0 || strength <= 0.0 || directionLength < 0.0001) {
        return vec3(0.0);
    }

    vec2 direction = windDirection / directionLength;
    // Match the handedness of the Blender Z-up preview after Y-up export.
    vec2 across = vec2(direction.y, -direction.x);
    float cycle = 6.28318530718 * (seconds / 2.4) + phase;
    float rise = clamp(position.y / height, 0.0, 1.0);
    float bend = max((rise - 0.08) / 0.92, 0.0);
    bend *= bend;
    float gust = 0.5 + 0.5 * sin(cycle - 0.9);
    float forward = 0.115 * (0.20 + 0.55 * gust * gust + 0.20 * sin(cycle - 1.2 * rise));
    float lateral = 0.027 * sin(cycle - 1.4 * rise + 0.4);
    float radius = clamp(length(position.xz) / (0.33 * height), 0.0, 1.0);
    float flutter = 0.014 * radius * sin(3.0 * cycle + 2.0 * dot(position.xz, across) + 4.0 * rise);
    vec2 displacement = strength * height * bend * (forward * direction + (lateral + flutter) * across);
    return vec3(displacement.x, 0.0, displacement.y);
}

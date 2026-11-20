#version 450
#extension GL_GOOGLE_include_directive : require

#include "pine_wind.glsl"

layout(location = 0) in vec3 inPosition;
layout(location = 1) in vec3 inNormal;
layout(location = 2) in vec2 inUV;
layout(location = 3) in vec4 inTangent;

layout(set = 0, binding = 0, std140) uniform PineCamera {
    mat4 viewProjection;
} camera;

layout(push_constant, std430) uniform PineDraw {
    mat4 model;
    vec4 wind; // Local XZ direction, strength, time in seconds.
    vec4 tree; // Local height, phase in radians, two reserved floats.
} draw;

layout(location = 0) out vec2 outUV;
layout(location = 1) out vec3 outWorldNormal;
layout(location = 2) out vec4 outWorldTangent;
layout(location = 3) out vec3 outWorldPosition;

vec3 bendVertex(vec3 position) {
    return position + pineWindOffset(position, draw.tree.x, draw.wind.w,
                                     draw.wind.xy, draw.wind.z, draw.tree.y);
}

void main() {
    vec3 bent = bendVertex(inPosition);
    mat3 localFrame = mat3(1.0);
    if (draw.wind.z > 0.0 && draw.tree.x > 0.0 &&
        length(draw.wind.xy) >= 0.0001 && inPosition.y > 0.08 * draw.tree.x) {
        // Differentiate the bend so the normal map and tangent frame sway too.
        float stepSize = max(0.0005, 0.0005 * draw.tree.x);
        localFrame = mat3(
            bendVertex(inPosition + vec3(stepSize, 0.0, 0.0)) - bent,
            bendVertex(inPosition + vec3(0.0, stepSize, 0.0)) - bent,
            bendVertex(inPosition + vec3(0.0, 0.0, stepSize)) - bent
        ) / stepSize;
    }
    mat3 worldFrame = mat3(draw.model) * localFrame;
    vec3 normal = normalize(transpose(inverse(worldFrame)) * inNormal);
    vec3 tangent = worldFrame * inTangent.xyz;
    tangent = normalize(tangent - normal * dot(normal, tangent));
    float handedness = inTangent.w * (determinant(worldFrame) < 0.0 ? -1.0 : 1.0);

    vec4 world = draw.model * vec4(bent, 1.0);
    gl_Position = camera.viewProjection * world;
    outUV = inUV;
    outWorldNormal = normal;
    outWorldTangent = vec4(tangent, handedness);
    outWorldPosition = world.xyz;
}

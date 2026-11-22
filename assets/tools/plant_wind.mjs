// Directional wind for the rigged catalog GLBs loaded with a Three.js GLTFLoader.
const PERIOD = 12;
const MAX_WIND = 1.5;

function spring(position, velocity, target, frequency, damping, dt) {
    const omega = 2 * Math.PI * frequency;
    const decay = damping * omega;
    const oscillation = omega * Math.sqrt(1 - damping * damping);
    const displacement = position - target;
    const sine = Math.sin(oscillation * dt);
    const cosine = Math.cos(oscillation * dt);
    const envelope = Math.exp(-decay * dt);

    // Exact underdamped spring step with a constant target over this frame.
    return [
        target + envelope * (displacement * cosine + (velocity + decay * displacement) * sine / oscillation),
        envelope * (velocity * cosine - (decay * velocity + omega * omega * displacement) * sine / oscillation),
    ];
}

export class PlantWind {
    constructor(scene, phaseSeconds = 0) {
        if (!Number.isFinite(phaseSeconds)) {
            throw new RangeError("Plant wind phase must be finite");
        }
        this.time = phaseSeconds % PERIOD;
        this.joints = [];
        scene.traverse((node) => {
            const profile = node.userData?.plantWind;
            if (node.isBone && profile) {
                this.joints.push({ node, ...profile, x: 0, z: 0, vx: 0, vz: 0 });
            }
        });
        if (!this.joints.length) {
            throw new Error("PlantWind requires a rigged plant GLB");
        }
    }

    // The plant-local XZ wind vector points downwind. Its length is strength.
    update(deltaSeconds, windX, windZ) {
        if (![deltaSeconds, windX, windZ].every(Number.isFinite) || deltaSeconds < 0) {
            throw new RangeError("Plant wind needs finite inputs and a nonnegative time step");
        }
        this.time = (this.time + deltaSeconds % PERIOD) % PERIOD;
        const phase = 2 * Math.PI * this.time / PERIOD;
        const magnitude = Math.hypot(windX, windZ);
        const limit = magnitude > MAX_WIND ? MAX_WIND / magnitude : 1;
        const gust = limit * (0.85 + 0.15 * Math.sin(phase) + 0.10 * Math.sin(3 * phase + 0.6));
        const harmonics = [Math.cos(7 * phase), Math.sin(7 * phase), Math.cos(13 * phase), Math.sin(13 * phase)];

        for (const joint of this.joints) {
            [joint.x, joint.vx] = spring(joint.x, joint.vx, windX * gust, joint.frequency, joint.damping, deltaSeconds);
            [joint.z, joint.vz] = spring(joint.z, joint.vz, windZ * gust, joint.frequency, joint.damping, deltaSeconds);
            // Use the spring's wind vector for both bend and flutter so reversing
            // the wind preserves inertia and still air lets the limbs settle.
            const flutter = joint.flutter.reduce((sum, coefficient, i) => sum + coefficient * harmonics[i], 0);
            const dx = joint.x * joint.gain - joint.z * flutter;
            const dz = joint.z * joint.gain + joint.x * flutter;
            const [ax, ay, az] = joint.axis;
            // Cross the limb direction with its desired displacement.
            const rx = ay * dz;
            const ry = az * dx - ax * dz;
            const rz = -ay * dx;
            const angle = Math.hypot(rx, ry, rz);
            const multiplier = angle > 1e-8 ? Math.sin(angle / 2) / angle : 0.5;
            joint.node.quaternion.set(rx * multiplier, ry * multiplier, rz * multiplier, Math.cos(angle / 2));
        }
    }
}

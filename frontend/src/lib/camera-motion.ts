/**
 * Camera motion helpers for rendering reference-frame zone polygons on
 * the current video frame.
 *
 * Convention (matches process.py / motion_compensator.py):
 *   matrix_ref_to_cur maps reference-frame pixel coordinates to
 *   current-frame pixel coordinates.
 *
 *   p_current = M @ [px_ref, py_ref, 1]^T
 *
 * where M is the 2×3 affine matrix stored as [[a,b,c],[d,e,f]].
 * The identity matrix means the camera has not moved (or motion is below
 * the deadband).
 */

/** A 2×3 affine matrix stored row-major: [[a,b,c],[d,e,f]]. */
export type AffineMatrix = [[number, number, number], [number, number, number]];

/** Per-frame entry from camera_motion.json. */
export interface FrameMotion {
    frame: number;
    dx: number;
    dy: number;
    angle_deg: number;
    magnitude_px: number;
    matrix_ref_to_cur: AffineMatrix;
}

/** Full camera_motion.json structure. */
export interface CameraMotionData {
    compensation_enabled: boolean;
    scale: number;
    deadband_px: number;
    convention?: string;
    frames: FrameMotion[];
}

const IDENTITY: AffineMatrix = [
    [1, 0, 0],
    [0, 1, 0],
];

function isIdentity(m: AffineMatrix): boolean {
    return (
        m[0][0] === 1 && m[0][1] === 0 && m[0][2] === 0 &&
        m[1][0] === 0 && m[1][1] === 1 && m[1][2] === 0
    );
}

/**
 * Apply a 2×3 affine matrix to a single (x, y) point.
 *
 * Returns the transformed point (not rounded — caller decides precision).
 */
export function applyAffine(
    point: readonly [number, number],
    matrix: AffineMatrix,
): [number, number] {
    const [x, y] = point;
    const [[a, b, c], [d, e, f]] = matrix;
    return [a * x + b * y + c, d * x + e * y + f];
}

/**
 * Warp every vertex of a polygon using the given affine matrix.
 *
 * @param poly    Array of (x, y) pairs in reference-frame coordinates.
 * @param matrix  2×3 reference→current affine matrix.
 * @returns       New polygon array in current-frame coordinates.
 */
export function warpPolygon(
    poly: ReadonlyArray<readonly [number, number]>,
    matrix: AffineMatrix,
): [number, number][] {
    if (isIdentity(matrix)) return poly.map(([x, y]) => [x, y]);
    return poly.map((pt) => applyAffine(pt, matrix));
}

/**
 * Build a Map from frame number → AffineMatrix from the frames array in
 * camera_motion.json. Frames that are not present (e.g. the file is sparse)
 * are not in the map; callers should fall back to identity when not found.
 */
export function buildFrameMotionMap(
    frames: FrameMotion[],
): Map<number, AffineMatrix> {
    const map = new Map<number, AffineMatrix>();
    for (const entry of frames) {
        map.set(entry.frame, entry.matrix_ref_to_cur);
    }
    return map;
}

/**
 * Look up the reference→current matrix for the given frame number.
 *
 * Returns the identity matrix when:
 * - the map is null / empty (no motion data available), or
 * - the exact frame is not in the map (below-deadband frames are omitted).
 *
 * The returned matrix can be passed directly to warpPolygon().
 */
export function getFrameMatrix(
    map: Map<number, AffineMatrix> | null,
    frame: number,
): AffineMatrix {
    if (!map || map.size === 0) return IDENTITY;
    return map.get(frame) ?? IDENTITY;
}

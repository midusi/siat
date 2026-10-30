/**
 * Camera motion helpers for rendering reference-frame zone polygons on
 * the current video frame.
 *
 * Convention (matches process.py / motion_compensator.py):
 *   matrix_ref_to_cur maps reference-frame pixel coordinates to
 *   current-frame pixel coordinates.
 *
 * New format (matrix_format === "homography_3x3"):
 *   p_current = H @ [px_ref, py_ref, 1]^T   (divide by third component)
 *   H is stored as [[a,b,c],[d,e,f],[g,h,i]] (3×3 row-major).
 *
 * Legacy format (no matrix_format key, or matrix has 2 rows):
 *   p_current = M @ [px_ref, py_ref, 1]^T   (no division needed)
 *   M is stored as [[a,b,c],[d,e,f]] (2×3 row-major).
 *
 * Both formats are supported transparently via the MotionMatrix union type.
 */

/** A 2×3 affine matrix stored row-major: [[a,b,c],[d,e,f]]. */
export type AffineMatrix = [[number, number, number], [number, number, number]];

/** A 3×3 projective homography stored row-major. */
export type HomographyMatrix = [
	[number, number, number],
	[number, number, number],
	[number, number, number]
];

/** Either a 2×3 affine (legacy) or a 3×3 homography (current). */
export type MotionMatrix = AffineMatrix | HomographyMatrix;

/** Per-frame entry from camera_motion.json. */
export interface FrameMotion {
	frame: number;
	dx: number;
	dy: number;
	angle_deg: number;
	magnitude_px: number;
	matrix_ref_to_cur: MotionMatrix;
}

/** Full camera_motion.json structure. */
export interface CameraMotionData {
	compensation_enabled: boolean;
	scale: number;
	/** Present in files produced by the 3x3 homography code. */
	matrix_format?: string;
	/** Present in legacy files; not used by the frontend logic. */
	deadband_px?: number;
	smooth_sigma?: number;
	anchor_interval?: number;
	convention?: string;
	frames: FrameMotion[];
}

const IDENTITY_3X3: HomographyMatrix = [
	[1, 0, 0],
	[0, 1, 0],
	[0, 0, 1]
];

function isAffine(m: MotionMatrix): m is AffineMatrix {
	return m.length === 2;
}

function isIdentity(m: MotionMatrix): boolean {
	if (isAffine(m)) {
		return (
			m[0][0] === 1 &&
			m[0][1] === 0 &&
			m[0][2] === 0 &&
			m[1][0] === 0 &&
			m[1][1] === 1 &&
			m[1][2] === 0
		);
	}
	const h = m as HomographyMatrix;
	return (
		h[0][0] === 1 &&
		h[0][1] === 0 &&
		h[0][2] === 0 &&
		h[1][0] === 0 &&
		h[1][1] === 1 &&
		h[1][2] === 0 &&
		h[2][0] === 0 &&
		h[2][1] === 0 &&
		h[2][2] === 1
	);
}

/**
 * Apply a 2×3 affine matrix to a single (x, y) point.
 *
 * Returns the transformed point (not rounded — caller decides precision).
 */
export function applyAffine(
	point: readonly [number, number],
	matrix: AffineMatrix
): [number, number] {
	const [x, y] = point;
	const [[a, b, c], [d, e, f]] = matrix;
	return [a * x + b * y + c, d * x + e * y + f];
}

/**
 * Apply a 3×3 projective homography to a single (x, y) point.
 *
 * Divides by the homogeneous coordinate (w) so the result is in Cartesian
 * pixel space.  Returns the transformed point (not rounded).
 */
export function applyHomography(
	point: readonly [number, number],
	matrix: HomographyMatrix
): [number, number] {
	const [x, y] = point;
	const [[a, b, c], [d, e, f], [g, h, i]] = matrix;
	const w = g * x + h * y + i;
	if (Math.abs(w) < 1e-10) {
		// Degenerate: return point unchanged rather than Infinity
		return [x, y];
	}
	return [(a * x + b * y + c) / w, (d * x + e * y + f) / w];
}

/**
 * Apply either a 2×3 affine or a 3×3 homography to a single point.
 *
 * Dispatches automatically based on matrix dimensions, so callers do not
 * need to know which format the camera_motion.json was produced with.
 */
export function applyTransform(
	point: readonly [number, number],
	matrix: MotionMatrix
): [number, number] {
	if (isAffine(matrix)) {
		return applyAffine(point, matrix);
	}
	return applyHomography(point, matrix as HomographyMatrix);
}

/**
 * Warp every vertex of a polygon using the given motion matrix (affine or
 * homography).
 *
 * @param poly    Array of (x, y) pairs in reference-frame coordinates.
 * @param matrix  2×3 affine or 3×3 homography (reference→current).
 * @returns       New polygon array in current-frame coordinates.
 */
export function warpPolygon(
	poly: ReadonlyArray<readonly [number, number]>,
	matrix: MotionMatrix
): [number, number][] {
	if (isIdentity(matrix)) return poly.map(([x, y]) => [x, y]);
	return poly.map((pt) => applyTransform(pt, matrix));
}

/**
 * Build a Map from frame number → MotionMatrix from the frames array in
 * camera_motion.json.  Frames absent from the file are not in the map;
 * callers should fall back to identity when not found.
 */
export function buildFrameMotionMap(frames: FrameMotion[]): Map<number, MotionMatrix> {
	const map = new Map<number, MotionMatrix>();
	for (const entry of frames) {
		map.set(entry.frame, entry.matrix_ref_to_cur);
	}
	return map;
}

/**
 * Look up the reference→current matrix for the given frame number.
 *
 * Returns the 3×3 identity when:
 * - the map is null / empty (no motion data available), or
 * - the exact frame is not in the map.
 *
 * The returned matrix can be passed directly to warpPolygon().
 */
export function getFrameMatrix(map: Map<number, MotionMatrix> | null, frame: number): MotionMatrix {
	if (!map || map.size === 0) return IDENTITY_3X3;
	return map.get(frame) ?? IDENTITY_3X3;
}

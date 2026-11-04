import type { Vertex } from './review';

type MatrixRow = [number, number, number];
type AffineMatrix = [MatrixRow, MatrixRow];
type HomographyMatrix = [MatrixRow, MatrixRow, MatrixRow];
export type MotionMatrix = AffineMatrix | HomographyMatrix;
export type FrameMotionMap = Map<number, MotionMatrix>;
type FrameMotion = { frame: number; matrix_ref_to_cur: MotionMatrix };
export type CameraMotionData = { frames: Array<FrameMotion> };

const IDENTITY: HomographyMatrix = [
	[1, 0, 0],
	[0, 1, 0],
	[0, 0, 1]
];
const MIN_HOMOGENEOUS_WEIGHT: number = 1e-10;

const isAffine = (matrix: MotionMatrix): matrix is AffineMatrix => matrix.length === 2;

const applyRow = (row: MatrixRow, [x, y]: Vertex): number => row[0] * x + row[1] * y + row[2];

const applyAffine = (point: Vertex, [rowX, rowY]: AffineMatrix): Vertex => [
	applyRow(rowX, point),
	applyRow(rowY, point)
];

const applyHomography = (point: Vertex, [rowX, rowY, rowW]: HomographyMatrix): Vertex => {
	const weight: number = applyRow(rowW, point);
	if (Math.abs(weight) < MIN_HOMOGENEOUS_WEIGHT) {
		return point;
	}
	return [applyRow(rowX, point) / weight, applyRow(rowY, point) / weight];
};

const applyTransform = (point: Vertex, matrix: MotionMatrix): Vertex =>
	isAffine(matrix) ? applyAffine(point, matrix) : applyHomography(point, matrix);

export const warpPolygon = (polygon: Array<Vertex>, matrix: MotionMatrix): Array<Vertex> =>
	matrix === IDENTITY
		? polygon
		: polygon.map((point: Vertex): Vertex => applyTransform(point, matrix));

export const buildFrameMotionMap = (frames: Array<FrameMotion>): FrameMotionMap =>
	new Map(
		frames.map((entry: FrameMotion): [number, MotionMatrix] => [
			entry.frame,
			entry.matrix_ref_to_cur
		])
	);

export const getFrameMatrix = (motionMap: FrameMotionMap | null, frame: number): MotionMatrix =>
	motionMap?.get(frame) ?? IDENTITY;

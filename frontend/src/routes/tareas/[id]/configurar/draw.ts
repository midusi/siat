import { centroid, toCanvasPx } from './geometry';
import { defaultColorForSentido, hexToRgba } from '$lib/polygon-utils';

import type { Coordinates, Polygon } from './geometry';

type InProgressStyle = { line: string; point: string };
export type Scene = {
	currentPoints: Array<Coordinates>;
	editMode: boolean;
	excludedMode: boolean;
	pending: Omit<Polygon, 'id'> | null;
	polygons: Array<Polygon>;
	selectedId: number | null;
};

const EXCLUDED_COLOR: string = 'rgba(0, 0, 0, 1)';
const FILL_ALPHA: number = 0.3;
const HANDLE_RADIUS: number = 8;
const IN_PROGRESS_COLOR: Record<'default' | 'excluded', InProgressStyle> = {
	default: { line: 'rgba(255, 255, 255, 0.8)', point: 'rgba(255, 255, 255, 1)' },
	excluded: { line: 'rgba(0, 0, 0, 1)', point: 'rgba(0, 0, 0, 1)' }
};
const PENDING_FILL_ALPHA: number = 0.5;
const POINT_RADIUS: number = 6;
const SELECTION_STROKE: string = 'rgba(255, 255, 255, 0.85)';

const tracePath = (ctx: CanvasRenderingContext2D, points: Array<Coordinates>): void => {
	ctx.beginPath();
	ctx.moveTo(points[0].x, points[0].y);
	for (const p of points.slice(1)) {
		ctx.lineTo(p.x, p.y);
	}
};

const drawLabel = (ctx: CanvasRenderingContext2D, text: string, at: Coordinates): void => {
	ctx.font = 'bold 14px sans-serif';
	ctx.fillStyle = 'white';
	ctx.textAlign = 'center';
	ctx.textBaseline = 'middle';
	ctx.shadowColor = 'black';
	ctx.shadowBlur = 5;
	ctx.fillText(text, at.x, at.y);
	ctx.shadowBlur = 0;
};

const polygonHex = (poly: Omit<Polygon, 'id'>): string =>
	poly.color ?? defaultColorForSentido(poly.sentido);

const drawPolygon = (
	ctx: CanvasRenderingContext2D,
	poly: Omit<Polygon, 'id'>,
	pending: boolean,
	selected: boolean
): void => {
	const vertices: Array<Coordinates> = toCanvasPx(poly.vertices, ctx.canvas);
	const excluded: boolean = poly.sentido === 'Excluida';
	const hex: string = polygonHex(poly);
	tracePath(ctx, vertices);
	ctx.closePath();
	ctx.fillStyle = excluded
		? EXCLUDED_COLOR
		: hexToRgba(hex, pending ? PENDING_FILL_ALPHA : FILL_ALPHA);
	ctx.fill();
	ctx.strokeStyle = excluded ? EXCLUDED_COLOR : hexToRgba(hex, 1);
	ctx.lineWidth = pending ? 4 : 2;
	ctx.setLineDash(pending ? [8, 4] : []);
	ctx.stroke();
	ctx.setLineDash([]);
	if (selected && !pending) {
		tracePath(ctx, vertices);
		ctx.closePath();
		ctx.strokeStyle = SELECTION_STROKE;
		ctx.lineWidth = 2;
		ctx.setLineDash([5, 3]);
		ctx.stroke();
		ctx.setLineDash([]);
	}
	if (!pending) {
		drawLabel(ctx, poly.via, centroid(vertices));
	}
};

const drawVertexHandles = (ctx: CanvasRenderingContext2D, poly: Polygon): void => {
	ctx.strokeStyle = polygonHex(poly);
	ctx.lineWidth = 2;
	for (const v of toCanvasPx(poly.vertices, ctx.canvas)) {
		ctx.beginPath();
		ctx.arc(v.x, v.y, HANDLE_RADIUS, 0, Math.PI * 2);
		ctx.fillStyle = 'white';
		ctx.fill();
		ctx.stroke();
	}
};

const drawInProgress = (
	ctx: CanvasRenderingContext2D,
	points: Array<Coordinates>,
	excludedMode: boolean
): void => {
	const vertices: Array<Coordinates> = toCanvasPx(points, ctx.canvas);
	const color: InProgressStyle = IN_PROGRESS_COLOR[excludedMode ? 'excluded' : 'default'];
	tracePath(ctx, vertices);
	ctx.strokeStyle = color.line;
	ctx.lineWidth = 2;
	ctx.setLineDash([6, 6]);
	ctx.stroke();
	ctx.setLineDash([]);
	ctx.fillStyle = color.point;
	for (const p of vertices) {
		ctx.beginPath();
		ctx.arc(p.x, p.y, POINT_RADIUS, 0, Math.PI * 2);
		ctx.fill();
	}
};

export const redraw = (ctx: CanvasRenderingContext2D, scene: Scene): void => {
	ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
	const roads: Array<Polygon> = scene.polygons.filter((p) => p.sentido !== 'Excluida');
	const excluded: Array<Polygon> = scene.polygons.filter((p) => p.sentido === 'Excluida');
	for (const poly of [...roads, ...excluded]) {
		drawPolygon(ctx, poly, false, poly.id === scene.selectedId);
	}
	const selected: Polygon | undefined = scene.polygons.find((p) => p.id === scene.selectedId);
	if (scene.editMode && selected) {
		drawVertexHandles(ctx, selected);
	}
	if (scene.pending) {
		drawPolygon(ctx, scene.pending, true, false);
	}
	if (scene.currentPoints.length > 0) {
		drawInProgress(ctx, scene.currentPoints, scene.excludedMode);
	}
};

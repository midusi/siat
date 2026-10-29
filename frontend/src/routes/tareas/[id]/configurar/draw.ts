import { centroid, toCanvasPx } from './geometry';

import type { Coordinates, Polygon, Sentido } from './geometry';

type InProgressStyle = { line: string; point: string };
type PolygonStyle = { fill: string; pendingFill: string; stroke: string };
export type Scene = {
	currentPoints: Array<Coordinates>;
	excludedMode: boolean;
	pending: Omit<Polygon, 'id'> | null;
	polygons: Array<Polygon>;
};

const IN_PROGRESS_COLOR: Record<'default' | 'excluded', InProgressStyle> = {
	default: { line: 'rgba(255, 255, 255, 0.8)', point: 'rgba(255, 255, 255, 1)' },
	excluded: { line: 'rgba(0, 0, 0, 1)', point: 'rgba(0, 0, 0, 1)' }
};
const POINT_RADIUS: number = 6;
const POLYGON_STYLES: Record<Sentido, PolygonStyle> = {
	Entrada: {
		fill: 'rgba(74, 222, 128, 0.3)',
		pendingFill: 'rgba(74, 222, 128, 0.5)',
		stroke: 'rgba(74, 222, 128, 1)'
	},
	Excluida: {
		fill: 'rgba(0, 0, 0, 1)',
		pendingFill: 'rgba(0, 0, 0, 1)',
		stroke: 'rgba(0, 0, 0, 1)'
	},
	Salida: {
		fill: 'rgba(248, 113, 113, 0.3)',
		pendingFill: 'rgba(248, 113, 113, 0.5)',
		stroke: 'rgba(248, 113, 113, 1)'
	}
};

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

const drawPolygon = (
	ctx: CanvasRenderingContext2D,
	poly: Omit<Polygon, 'id'>,
	pending: boolean
): void => {
	const vertices: Array<Coordinates> = toCanvasPx(poly.vertices, ctx.canvas);
	const style: PolygonStyle = POLYGON_STYLES[poly.sentido];
	tracePath(ctx, vertices);
	ctx.closePath();
	ctx.fillStyle = pending ? style.pendingFill : style.fill;
	ctx.fill();
	ctx.strokeStyle = style.stroke;
	ctx.lineWidth = pending ? 4 : 2;
	ctx.setLineDash(pending ? [8, 4] : []);
	ctx.stroke();
	ctx.setLineDash([]);
	if (!pending) {
		drawLabel(ctx, poly.via, centroid(vertices));
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
	for (const poly of scene.polygons.filter((p) => p.sentido !== 'Excluida')) {
		drawPolygon(ctx, poly, false);
	}
	for (const poly of scene.polygons.filter((p) => p.sentido === 'Excluida')) {
		drawPolygon(ctx, poly, false);
	}
	if (scene.pending) {
		drawPolygon(ctx, scene.pending, true);
	}
	if (scene.currentPoints.length > 0) {
		drawInProgress(ctx, scene.currentPoints, scene.excludedMode);
	}
};

import type { AbsolutePoint, Road, TaskConfigPayload } from '$lib/types/task';

export type Coordinates = { x: number; y: number };
export type Polygon = {
	id: number;
	via: string;
	sentido: Sentido;
	vertices: Array<Coordinates>;
	color?: string;
};
export type Sentido = 'Entrada' | 'Excluida' | 'Salida';
export type Size = { width: number; height: number };

export const centroid = (points: Array<Coordinates>): Coordinates => {
	const n: number = points.length || 1;
	const sum: Coordinates = points.reduce((acc, p) => ({ x: acc.x + p.x, y: acc.y + p.y }), {
		x: 0,
		y: 0
	});
	return { x: sum.x / n, y: sum.y / n };
};

export const sortVertices = (points: Array<Coordinates>): Array<Coordinates> => {
	if (points.length < 3) {
		return points;
	}
	const center: Coordinates = centroid(points);
	return points
		.map(({ x, y }) => ({ x, y, angle: Math.atan2(y - center.y, x - center.x) }))
		.sort((a, b) => a.angle - b.angle)
		.map(({ x, y }) => ({ x, y }));
};

export const toCanvasPx = (points: Array<Coordinates>, target: Size): Array<Coordinates> =>
	points.map((p) => ({ x: p.x * target.width, y: p.y * target.height }));

export const toAbsolute = (point: Coordinates, frame: Size): AbsolutePoint => [
	Math.round(point.x * frame.width),
	Math.round(point.y * frame.height)
];

export const buildConfigPayload = (polygons: Array<Polygon>, frame: Size): TaskConfigPayload => {
	const verticesOf = (p: Polygon): Array<AbsolutePoint> =>
		p.vertices.map((v) => toAbsolute(v, frame));
	const roadsOf = (sentido: Sentido): Array<Road> =>
		polygons
			.filter((p) => p.sentido === sentido)
			.map((p) => ({ name: p.via.trim(), polygon: verticesOf(p) }));
	return {
		roads_in: roadsOf('Entrada'),
		roads_out: roadsOf('Salida'),
		excluded_zones: polygons.filter((p) => p.sentido === 'Excluida').map(verticesOf)
	};
};

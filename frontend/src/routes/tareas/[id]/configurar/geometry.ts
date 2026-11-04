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

const clamp01 = (value: number): number => Math.max(0, Math.min(1, value));

const clampPoint = (point: Coordinates): Coordinates => ({
	x: clamp01(point.x),
	y: clamp01(point.y)
});

export const movePolygon = (
	vertices: Array<Coordinates>,
	dx: number,
	dy: number
): Array<Coordinates> => vertices.map((v) => clampPoint({ x: v.x + dx, y: v.y + dy }));

export const moveVertex = (
	vertices: Array<Coordinates>,
	index: number,
	target: Coordinates
): Array<Coordinates> => vertices.map((v, i) => (i === index ? clampPoint(target) : v));

export const isPointInPolygon = (point: Coordinates, vertices: Array<Coordinates>): boolean => {
	let inside: boolean = false;
	for (
		let current = 0, previous = vertices.length - 1;
		current < vertices.length;
		previous = current++
	) {
		const start: Coordinates = vertices[current];
		const end: Coordinates = vertices[previous];
		const crossesRay: boolean =
			start.y > point.y !== end.y > point.y &&
			point.x < ((end.x - start.x) * (point.y - start.y)) / (end.y - start.y) + start.x;
		if (crossesRay) {
			inside = !inside;
		}
	}
	return inside;
};

export const nearestVertexIndex = (
	point: Coordinates,
	vertices: Array<Coordinates>,
	radius: Coordinates
): number => {
	let nearest: number = -1;
	let nearestDistance: number = 1;
	vertices.forEach((v, index) => {
		const dx: number = (v.x - point.x) / radius.x;
		const dy: number = (v.y - point.y) / radius.y;
		const distance: number = dx * dx + dy * dy;
		if (distance < nearestDistance) {
			nearest = index;
			nearestDistance = distance;
		}
	});
	return nearest;
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

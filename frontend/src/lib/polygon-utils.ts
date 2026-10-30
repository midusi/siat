/**
 * Pure geometry helpers for polygon editing operations.
 * All coordinates are relative (0–1) unless otherwise noted.
 * Extracted for potential future unit testing.
 */

export type RelPoint = { x: number; y: number };

/** Move all vertices by (dx, dy), clamped to [0, 1]. */
export function movePolygon(vertices: RelPoint[], dx: number, dy: number): RelPoint[] {
	return vertices.map((v) => ({
		x: Math.max(0, Math.min(1, v.x + dx)),
		y: Math.max(0, Math.min(1, v.y + dy))
	}));
}

/** Replace a single vertex at `index` with (nx, ny), clamped to [0, 1]. */
export function moveVertex(
	vertices: RelPoint[],
	index: number,
	nx: number,
	ny: number
): RelPoint[] {
	return vertices.map((v, i) =>
		i === index ? { x: Math.max(0, Math.min(1, nx)), y: Math.max(0, Math.min(1, ny)) } : v
	);
}

/**
 * Return a copy of the vertices shifted by offsetX/offsetY, clamped to [0, 1].
 * Used to create a visible duplicate of an existing polygon.
 */
export function duplicatePolygon(vertices: RelPoint[], offsetX = 0.03, offsetY = 0.03): RelPoint[] {
	return vertices.map((v) => ({
		x: Math.max(0, Math.min(1, v.x + offsetX)),
		y: Math.max(0, Math.min(1, v.y + offsetY))
	}));
}

/**
 * Ray-casting point-in-polygon test.
 * Returns true if (px, py) is strictly inside the polygon defined by `vertices`.
 */
export function isPointInPolygon(px: number, py: number, vertices: RelPoint[]): boolean {
	const n = vertices.length;
	let inside = false;
	for (let i = 0, j = n - 1; i < n; j = i++) {
		const xi = vertices[i].x,
			yi = vertices[i].y;
		const xj = vertices[j].x,
			yj = vertices[j].y;
		if (yi > py !== yj > py && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) {
			inside = !inside;
		}
	}
	return inside;
}

/**
 * Return the index of the nearest vertex within an elliptical threshold,
 * or -1 if none is within reach.
 * `thresholdX` and `thresholdY` are radii in relative coords.
 */
export function nearestVertexIndex(
	px: number,
	py: number,
	vertices: RelPoint[],
	thresholdX: number,
	thresholdY: number
): number {
	let best = -1;
	let bestDist = Infinity;
	for (let i = 0; i < vertices.length; i++) {
		const dx = (vertices[i].x - px) / thresholdX;
		const dy = (vertices[i].y - py) / thresholdY;
		const dist = dx * dx + dy * dy;
		if (dist < 1 && dist < bestDist) {
			bestDist = dist;
			best = i;
		}
	}
	return best;
}

/**
 * Default canvas stroke/fill color for a given polygon sentido.
 * Returns a CSS hex color string.
 */
export function defaultColorForSentido(sentido: string): string {
	if (sentido === 'Entrada') return '#4ade80';
	if (sentido === 'Salida') return '#f87171';
	return '#000000'; // Excluida
}

/**
 * Convert a CSS hex color and alpha to an rgba() string.
 */
export function hexToRgba(hex: string, alpha: number): string {
	const m = /^#?([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i.exec(hex);
	if (!m) return `rgba(0,0,0,${alpha})`;
	const r = parseInt(m[1], 16);
	const g = parseInt(m[2], 16);
	const b = parseInt(m[3], 16);
	return `rgba(${r},${g},${b},${alpha})`;
}

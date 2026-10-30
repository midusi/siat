import {
	duplicatePolygon as offsetVertices,
	isPointInPolygon,
	movePolygon,
	moveVertex,
	nearestVertexIndex
} from '$lib/polygon-utils';
import { sortVertices } from './geometry';

import type { Coordinates, Polygon, Sentido } from './geometry';

export type EditorCursor = 'crosshair' | 'default' | 'grab' | 'grabbing';
export type PendingPolygon = Omit<Polygon, 'id'>;
export type PolygonEditor = {
	readonly canConfirm: boolean;
	readonly currentPoints: Array<Coordinates>;
	readonly cursor: EditorCursor;
	readonly editMode: boolean;
	readonly entradasCount: number;
	readonly excludedMode: boolean;
	readonly pending: PendingPolygon | null;
	readonly polygons: Array<Polygon>;
	readonly salidasCount: number;
	readonly selectedId: number | null;
	addPoint: (point: Coordinates) => boolean;
	cancelPending: () => void;
	confirmPending: () => void;
	duplicatePolygon: (id: number) => void;
	handleKey: (key: string) => void;
	pointerDown: (point: Coordinates, handleRadius: Coordinates) => void;
	pointerMove: (point: Coordinates, handleRadius: Coordinates) => void;
	pointerUp: () => void;
	removePolygon: (id: number) => void;
	renamePolygon: (id: number, via: string) => void;
	setEditMode: (flag: boolean) => void;
	setExcludedMode: (flag: boolean) => void;
	setPolygonColor: (id: number, color: string) => void;
};

type Drag =
	| { type: 'move'; polygonId: number; start: Coordinates; original: Array<Coordinates> }
	| { type: 'vertex'; polygonId: number; vertexIndex: number };

const MIN_EXCLUDED_VERTICES: number = 3;
export const OPCIONES_SENTIDO: Array<Sentido> = ['Entrada', 'Salida'];
const ROAD_VERTICES: number = 4;

export const createPolygonEditor = (): PolygonEditor => {
	let currentPoints: Array<Coordinates> = $state([]);
	let cursor: EditorCursor = $state('crosshair');
	let drag: Drag | null = null;
	let editMode: boolean = $state(false);
	let excludedMode: boolean = $state(false);
	let lastId: number = 0;
	let lastSentido: Sentido = OPCIONES_SENTIDO[0];
	let pending: PendingPolygon | null = $state<PendingPolygon | null>(null);
	let polygons: Array<Polygon> = $state([]);
	let selectedId: number | null = $state(null);

	const canConfirm: boolean = $derived(!!pending && pending.via.trim().length > 0);
	const entradasCount: number = $derived(polygons.filter((p) => p.sentido === 'Entrada').length);
	const salidasCount: number = $derived(polygons.filter((p) => p.sentido === 'Salida').length);

	const findPolygon = (id: number | null): Polygon | undefined => polygons.find((p) => p.id === id);

	const addPolygon = (poly: PendingPolygon): void => {
		lastId += 1;
		polygons.push({ id: lastId, ...poly });
	};

	const addPoint = (point: Coordinates): boolean => {
		if (pending || editMode) {
			return false;
		}
		currentPoints.push(point);
		if (excludedMode || currentPoints.length !== ROAD_VERTICES) {
			return false;
		}
		pending = { vertices: sortVertices(currentPoints), via: '', sentido: lastSentido };
		currentPoints = [];
		return true;
	};

	const cancelPending = (): void => {
		pending = null;
	};

	const closeExcludedZone = (): void => {
		if (currentPoints.length < MIN_EXCLUDED_VERTICES) {
			return;
		}
		const index: number = polygons.filter((p) => p.sentido === 'Excluida').length + 1;
		addPolygon({
			vertices: sortVertices(currentPoints),
			via: `Zona excluída ${index}`,
			sentido: 'Excluida'
		});
		currentPoints = [];
	};

	const confirmPending = (): void => {
		if (!pending || !canConfirm) {
			return;
		}
		lastSentido = pending.sentido;
		addPolygon({ ...pending, via: pending.via.trim() });
		pending = null;
	};

	const handleKey = (key: string): void => {
		if (pending) {
			if (key === 'Enter') {
				confirmPending();
			}
			if (key === 'Escape') {
				cancelPending();
			}
			return;
		}
		if (key === 'Enter' && excludedMode) {
			closeExcludedZone();
		}
		if (key === 'Escape') {
			currentPoints = [];
			if (editMode) {
				selectedId = null;
			}
		}
		if (key === 'Backspace' && !editMode) {
			currentPoints.pop();
		}
	};

	const vertexHitIndex = (point: Coordinates, handleRadius: Coordinates): number => {
		const selected: Polygon | undefined = findPolygon(selectedId);
		if (!selected) {
			return -1;
		}
		return nearestVertexIndex(point.x, point.y, selected.vertices, handleRadius.x, handleRadius.y);
	};

	const polygonAt = (point: Coordinates): Polygon | undefined =>
		polygons.findLast((p) => isPointInPolygon(point.x, point.y, p.vertices));

	const hoverCursor = (point: Coordinates, handleRadius: Coordinates): EditorCursor => {
		if (point.x < 0 || point.x > 1 || point.y < 0 || point.y > 1) {
			return 'default';
		}
		if (vertexHitIndex(point, handleRadius) >= 0) {
			return 'crosshair';
		}
		return polygonAt(point) ? 'grab' : 'default';
	};

	const pointerDown = (point: Coordinates, handleRadius: Coordinates): void => {
		if (!editMode) {
			return;
		}
		const vertexIndex: number = vertexHitIndex(point, handleRadius);
		if (selectedId !== null && vertexIndex >= 0) {
			drag = { type: 'vertex', polygonId: selectedId, vertexIndex };
			cursor = 'crosshair';
			return;
		}
		const hit: Polygon | undefined = polygonAt(point);
		if (!hit) {
			selectedId = null;
			return;
		}
		selectedId = hit.id;
		drag = {
			type: 'move',
			polygonId: hit.id,
			start: point,
			original: hit.vertices.map((v) => ({ ...v }))
		};
		cursor = 'grabbing';
	};

	const pointerMove = (point: Coordinates, handleRadius: Coordinates): void => {
		if (!editMode) {
			return;
		}
		if (!drag) {
			cursor = hoverCursor(point, handleRadius);
			return;
		}
		const poly: Polygon | undefined = findPolygon(drag.polygonId);
		if (!poly) {
			return;
		}
		poly.vertices =
			drag.type === 'move'
				? movePolygon(drag.original, point.x - drag.start.x, point.y - drag.start.y)
				: moveVertex(poly.vertices, drag.vertexIndex, point.x, point.y);
	};

	const pointerUp = (): void => {
		if (!drag) {
			return;
		}
		drag = null;
		cursor = 'default';
	};

	const duplicatePolygon = (id: number): void => {
		const poly: Polygon | undefined = findPolygon(id);
		if (!poly) {
			return;
		}
		addPolygon({
			via: `${poly.via} (copia)`,
			sentido: poly.sentido,
			vertices: offsetVertices(poly.vertices),
			color: poly.color
		});
	};

	const removePolygon = (id: number): void => {
		polygons = polygons.filter((p) => p.id !== id);
		if (selectedId === id) {
			selectedId = null;
		}
	};

	const renamePolygon = (id: number, via: string): void => {
		const poly: Polygon | undefined = findPolygon(id);
		if (poly && via.trim().length > 0) {
			poly.via = via.trim();
		}
	};

	const setPolygonColor = (id: number, color: string): void => {
		const poly: Polygon | undefined = findPolygon(id);
		if (poly) {
			poly.color = color;
		}
	};

	const setEditMode = (flag: boolean): void => {
		editMode = flag;
		cursor = flag ? 'default' : 'crosshair';
		if (flag) {
			pending = null;
			currentPoints = [];
		} else {
			selectedId = null;
			drag = null;
		}
	};

	const setExcludedMode = (flag: boolean): void => {
		if (excludedMode === flag) {
			return;
		}
		excludedMode = flag;
		currentPoints = [];
		pending = null;
	};

	return {
		get canConfirm(): boolean {
			return canConfirm;
		},
		get currentPoints(): Array<Coordinates> {
			return currentPoints;
		},
		get cursor(): EditorCursor {
			return cursor;
		},
		get editMode(): boolean {
			return editMode;
		},
		get entradasCount(): number {
			return entradasCount;
		},
		get excludedMode(): boolean {
			return excludedMode;
		},
		get pending(): PendingPolygon | null {
			return pending;
		},
		get polygons(): Array<Polygon> {
			return polygons;
		},
		get salidasCount(): number {
			return salidasCount;
		},
		get selectedId(): number | null {
			return selectedId;
		},
		addPoint,
		cancelPending,
		confirmPending,
		duplicatePolygon,
		handleKey,
		pointerDown,
		pointerMove,
		pointerUp,
		removePolygon,
		renamePolygon,
		setEditMode,
		setExcludedMode,
		setPolygonColor
	};
};

import { sortVertices } from './geometry';

import type { Coordinates, Polygon, Sentido } from './geometry';

export type PendingPolygon = Omit<Polygon, 'id'>;
export type PolygonEditor = ReturnType<typeof createPolygonEditor>;

const MIN_EXCLUDED_VERTICES: number = 3;
export const OPCIONES_SENTIDO: Array<Sentido> = ['Entrada', 'Salida'];
const ROAD_VERTICES: number = 4;

/**
 * Estado del dibujo de vías y zonas excluidas.
 * Las vías se cierran solas al cuarto click y quedan pendientes hasta que se les pone nombre;
 * las zonas excluidas se cierran con Enter (mínimo 3 vértices).
 */
export const createPolygonEditor = () => {
	let currentPoints: Array<Coordinates> = $state([]);
	let excludedMode: boolean = $state(false);
	let lastId: number = 0;
	let lastSentido: Sentido = OPCIONES_SENTIDO[0];
	let pending: PendingPolygon | null = $state<PendingPolygon | null>(null);
	let polygons: Array<Polygon> = $state([]);

	const canConfirm: boolean = $derived(!!pending && pending.via.trim().length > 0);
	const entradasCount: number = $derived(polygons.filter((p) => p.sentido === 'Entrada').length);
	const salidasCount: number = $derived(polygons.filter((p) => p.sentido === 'Salida').length);

	const addPolygon = (poly: PendingPolygon): void => {
		lastId += 1;
		polygons.push({ id: lastId, ...poly });
	};

	/** Devuelve `true` si el punto completó una vía y quedó pendiente de confirmar. */
	const addPoint = (point: Coordinates): boolean => {
		if (pending) {
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
		}
		if (key === 'Backspace') {
			currentPoints.pop();
		}
	};

	const removePolygon = (id: number): void => {
		polygons = polygons.filter((p) => p.id !== id);
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
		get canConfirm() {
			return canConfirm;
		},
		get currentPoints() {
			return currentPoints;
		},
		get entradasCount() {
			return entradasCount;
		},
		get excludedMode() {
			return excludedMode;
		},
		get pending() {
			return pending;
		},
		get polygons() {
			return polygons;
		},
		get salidasCount() {
			return salidasCount;
		},
		addPoint,
		cancelPending,
		confirmPending,
		handleKey,
		removePolygon,
		setExcludedMode
	};
};

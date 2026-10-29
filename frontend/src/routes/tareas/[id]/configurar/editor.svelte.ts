import { sortVertices } from './geometry';

import type { Coordinates, Polygon, Sentido } from './geometry';

export type PendingPolygon = Omit<Polygon, 'id'>;
export type PolygonEditor = {
	readonly canConfirm: boolean;
	readonly currentPoints: Array<Coordinates>;
	readonly entradasCount: number;
	readonly excludedMode: boolean;
	readonly pending: PendingPolygon | null;
	readonly polygons: Array<Polygon>;
	readonly salidasCount: number;
	addPoint: (point: Coordinates) => boolean;
	cancelPending: () => void;
	confirmPending: () => void;
	handleKey: (key: string) => void;
	removePolygon: (id: number) => void;
	setExcludedMode: (flag: boolean) => void;
};

const MIN_EXCLUDED_VERTICES: number = 3;
export const OPCIONES_SENTIDO: Array<Sentido> = ['Entrada', 'Salida'];
const ROAD_VERTICES: number = 4;

export const createPolygonEditor = (): PolygonEditor => {
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
		get canConfirm(): boolean {
			return canConfirm;
		},
		get currentPoints(): Array<Coordinates> {
			return currentPoints;
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
		addPoint,
		cancelPending,
		confirmPending,
		handleKey,
		removePolygon,
		setExcludedMode
	};
};

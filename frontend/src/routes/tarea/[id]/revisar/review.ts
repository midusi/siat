import { apiFetch } from '$lib/api';
import { apiError } from '$lib/services/errors';

export type Appearance = { frame: string; boundingBox: BoundingBox };
export type BoundingBox = [string, string, string, string];
export type Box = [number, number, number, number];
export type ConteoVehiculos = { [vehiculo: string]: number };
export type DisplayableBBox = {
	id: string;
	bbox: BoundingBox;
	hideAtTime: number;
	opacity: number;
	fadeRemoveAtMs?: number;
};
export type FilaTabla = {
	tipo: string;
	__key?: string;
	[key: string]: string | number | undefined;
};
export type FrameRange = { dur: number; first: number; last: number };
export type GeneralBBox = { id: string; box: Box };
export type History = { [trackId: string]: Appearance & { class: string } };
export type Indeterminado = {
	first_appearance: Appearance;
	last_appearance: Appearance;
	class: string;
	labels: { in: string; out: string };
};
export type Indeterminados = { [trackId: string]: Indeterminado };
export type ObjHistoryEntry = { act_frame: number; box: Box };
export type Point = { x: number; y: number };
export type Rect = { x: number; y: number; width: number; height: number };
export type RoadPoly = { id: number; name: string; direction: string; polygon: [number, number][] };
export type Rutas = { [entrada: string]: { [salida: string]: ConteoVehiculos } };
export type Scale = { x: number; y: number };
export type Tabla = { columnas: string[]; datos: FilaTabla[]; total: FilaTabla };
export type TrackPoint = { frame: number; box: Box };

export type TaskReview = {
	videoPath: string;
	videoWidth: number;
	videoHeight: number;
	videoFps: number;
	roadsIn: RoadPoly[];
	roadsOut: RoadPoly[];
	excludedZones: [number, number][][];
	rutas: Rutas;
	indeterminados: Indeterminados;
	determinados: Indeterminados;
	history: History;
	historyUrl: string | null;
};

export type TaskReviewChanges = {
	rutas: Rutas;
	indeterminados: Indeterminados;
	determinados: Indeterminados;
	trackHistory: Map<string, TrackPoint[]>;
};

type RawIndeterminado = Omit<Indeterminado, 'labels'> & {
	labels: Indeterminado['labels'] | [string, string];
};

const TASK_API: string = '/task';

const normalizeLabels = (
	items: Record<string, RawIndeterminado> | null | undefined
): Indeterminados => {
	const out: Indeterminados = {};
	for (const [id, it] of Object.entries(items ?? {})) {
		const labels = Array.isArray(it.labels)
			? { in: it.labels[0] ?? '', out: it.labels[1] ?? '' }
			: it.labels;
		out[id] = { ...it, labels };
	}
	return out;
};

const asArray = <T>(value: unknown): T[] => (Array.isArray(value) ? value : []);

export const fetchTaskReview = async (taskId: string): Promise<TaskReview> => {
	const res = await apiFetch(`${TASK_API}/${taskId}`);
	if (!res.ok) {
		throw await apiError(res, 'No se pudieron obtener los datos de la tarea');
	}
	const data = await res.json();
	return {
		videoPath: data.videoPath ?? '',
		videoWidth: Number(data.videoWidth),
		videoHeight: Number(data.videoHeight),
		videoFps: Number(data.videoFps),
		roadsIn: asArray(data.roadsIn),
		roadsOut: asArray(data.roadsOut),
		excludedZones: asArray(data.excludedZones),
		rutas: data.rutas ?? {},
		indeterminados: normalizeLabels(data.indeterminados),
		determinados: normalizeLabels(data.determinados),
		history: data.history ?? {},
		historyUrl: data.dataObjHistoryUrl || data.data_obj_history_url || data.historyUrl || null
	};
};

export const fetchTrackHistory = async (url: string): Promise<Map<string, TrackPoint[]>> => {
	const res = await fetch(`${url}${url.includes('?') ? '&' : '?'}_ts=${Date.now()}`);
	if (!res.ok) {
		throw new Error('Error al obtener data_obj_history.json');
	}
	const json = (await res.json()) as Record<string, ObjHistoryEntry[]>;
	const trackMap = new Map<string, TrackPoint[]>();
	for (const [trackId, entries] of Object.entries(json)) {
		const points = entries.map((e) => ({ frame: Number(e.act_frame), box: e.box }));
		trackMap.set(
			trackId,
			points.sort((a, b) => a.frame - b.frame)
		);
	}
	return trackMap;
};

const serializeTrackHistory = (
	trackMap: Map<string, TrackPoint[]>
): Record<string, ObjHistoryEntry[]> => {
	const out: Record<string, ObjHistoryEntry[]> = {};
	for (const [trackId, points] of trackMap.entries()) {
		out[trackId] = points
			.slice()
			.sort((a, b) => a.frame - b.frame)
			.map((p) => ({ act_frame: p.frame, box: p.box }));
	}
	return out;
};

export const updateTaskReview = async (taskId: string, changes: TaskReviewChanges) => {
	const res = await apiFetch(`${TASK_API}/${taskId}/update-data`, {
		method: 'POST',
		body: JSON.stringify({
			rutas: changes.rutas,
			indeterminados: changes.indeterminados,
			determinados: changes.determinados,
			data_obj_history: serializeTrackHistory(changes.trackHistory)
		})
	});
	if (!res.ok) {
		throw await apiError(res, 'No se pudo guardar los cambios en el servidor.');
	}
};

export const timeToFrame = (timeSec: number, range: FrameRange | null, fps: number): number => {
	if (!range) {
		return Math.floor(timeSec * (fps || 0));
	}
	const { dur, first, last } = range;
	const span = Math.max(0, last - first);
	const t = Math.min(Math.max(timeSec, 0), dur);
	const f = first + (span > 0 ? Math.round((t / dur) * span) : 0);
	return Math.max(first, Math.min(f, last));
};

export const frameToTime = (frame: number, range: FrameRange | null, fps: number): number => {
	if (!range) {
		return fps > 0 ? frame / fps : 0;
	}
	const { dur, first, last } = range;
	const span = Math.max(0, last - first);
	const clamped = Math.max(first, Math.min(frame, last));
	const t = span > 0 ? ((clamped - first) / span) * dur : 0;
	return Math.max(0, Math.min(t, dur));
};

export const isFrameWithinTrack = (points: TrackPoint[], frame: number): boolean => {
	if (!points.length) {
		return false;
	}
	return frame >= points[0].frame && frame <= points[points.length - 1].frame;
};

export const FADE_OUT_DURATION_SECONDS = 1.0;
export const OPACITY_TRANSITION_MS = 500;

export const fadeBoxes = (
	boxes: DisplayableBBox[],
	clock: number,
	nowMs: number
): DisplayableBBox[] => {
	const out: DisplayableBBox[] = [];
	for (const box of boxes) {
		const opacity = Math.max(0, Math.min(1, (box.hideAtTime - clock) / FADE_OUT_DURATION_SECONDS));
		if (opacity > 0) {
			const unchanged = opacity === box.opacity && !box.fadeRemoveAtMs;
			out.push(unchanged ? box : { ...box, opacity, fadeRemoveAtMs: undefined });
			continue;
		}
		const removeAt = box.fadeRemoveAtMs ?? nowMs + OPACITY_TRANSITION_MS;
		if (nowMs < removeAt) {
			out.push({ ...box, opacity: 0, fadeRemoveAtMs: removeAt });
		}
	}
	return out;
};

export const parseBoundingBox = (bbox: BoundingBox): Box => [
	parseFloat(bbox[0]),
	parseFloat(bbox[1]),
	parseFloat(bbox[2]),
	parseFloat(bbox[3])
];

export const toScaledClampedRect = (
	box: Box,
	scale: Scale,
	bounds: { width: number; height: number }
): Rect | null => {
	const [x1, y1, x2, y2] = box;
	let left = x1 * scale.x;
	let top = y1 * scale.y;
	let width = (x2 - x1) * scale.x;
	let height = (y2 - y1) * scale.y;
	if (width < 0) {
		left += width;
		width = Math.abs(width);
	}
	if (height < 0) {
		top += height;
		height = Math.abs(height);
	}
	if (left < 0) {
		width += left;
		left = 0;
	}
	if (top < 0) {
		height += top;
		top = 0;
	}
	if (left + width > bounds.width) {
		width = bounds.width - left;
	}
	if (top + height > bounds.height) {
		height = bounds.height - top;
	}
	if (width <= 0 || height <= 0) {
		return null;
	}
	return { x: left, y: top, width, height };
};

export const rectStyle = (rect: Rect): string => {
	return `left: ${rect.x}px; top: ${rect.y}px; width: ${rect.width}px; height: ${rect.height}px;`;
};

export const boxCenterScaled = (box: Box, scale: Scale): Point => {
	const [x1, y1, x2, y2] = box;
	return { x: ((x1 + x2) / 2) * scale.x, y: ((y1 + y2) / 2) * scale.y };
};

export const scalePolygon = (poly: [number, number][], scale: Scale): string => {
	return poly.map(([x, y]) => `${x * scale.x},${y * scale.y}`).join(' ');
};

type Intersection = Point & { t: number };

const segmentRectIntersections = (p1: Point, p2: Point, rect: Rect): Intersection[] => {
	const xL = rect.x;
	const xR = rect.x + rect.width;
	const yT = rect.y;
	const yB = rect.y + rect.height;
	const dx = p2.x - p1.x;
	const dy = p2.y - p1.y;
	const res: Intersection[] = [];
	const add = (t: number, x: number, y: number) => {
		if (t >= 0 && t <= 1) {
			res.push({ t, x, y });
		}
	};
	if (dx !== 0) {
		for (const edgeX of [xL, xR]) {
			const t = (edgeX - p1.x) / dx;
			const y = p1.y + t * dy;
			if (y >= yT && y <= yB) {
				add(t, edgeX, y);
			}
		}
	}
	if (dy !== 0) {
		for (const edgeY of [yT, yB]) {
			const t = (edgeY - p1.y) / dy;
			const x = p1.x + t * dx;
			if (x >= xL && x <= xR) {
				add(t, x, edgeY);
			}
		}
	}
	return res.sort((a, b) => a.t - b.t);
};

const isInsideRect = (p: Point, rect: Rect): boolean =>
	p.x >= rect.x && p.x <= rect.x + rect.width && p.y >= rect.y && p.y <= rect.y + rect.height;

export const clipPolyline = (pts: Point[], rect: Rect | null): Point[][] => {
	if (!rect) {
		return pts.length > 1 ? [pts] : [];
	}
	const out: Point[][] = [];
	let seg: Point[] = [];
	for (let i = 1; i < pts.length; i++) {
		const a = pts[i - 1];
		const b = pts[i];
		const inA = isInsideRect(a, rect);
		const inB = isInsideRect(b, rect);
		if (!inA && !inB) {
			const ints = segmentRectIntersections(a, b, rect);
			if (seg.length === 0) {
				seg.push(a);
			}
			if (ints.length === 2) {
				seg.push({ x: ints[0].x, y: ints[0].y });
				if (seg.length > 1) {
					out.push(seg);
				}
				seg = [{ x: ints[1].x, y: ints[1].y }];
			} else {
				seg.push(b);
			}
		} else if (inA && !inB) {
			const first = segmentRectIntersections(a, b, rect)[0];
			seg = first ? [{ x: first.x, y: first.y }, b] : [b];
		} else if (!inA && inB) {
			const last = segmentRectIntersections(a, b, rect).at(-1);
			if (seg.length === 0) {
				seg.push(a);
			}
			if (last) {
				seg.push({ x: last.x, y: last.y });
			}
			if (seg.length > 1) {
				out.push(seg);
			}
			seg = [];
		} else {
			if (seg.length > 1) {
				out.push(seg);
			}
			seg = [];
		}
	}
	if (seg.length > 1) {
		out.push(seg);
	}
	return out;
};

export const buildFrameMap = (trackMap: Map<string, TrackPoint[]>): Map<number, GeneralBBox[]> => {
	const frameMap = new Map<number, GeneralBBox[]>();
	for (const [trackId, points] of trackMap.entries()) {
		for (const p of points) {
			if (!frameMap.has(p.frame)) {
				frameMap.set(p.frame, []);
			}
			frameMap.get(p.frame)!.push({ id: trackId, box: p.box });
		}
	}
	return frameMap;
};

export const mergeTrackPoints = (keep: TrackPoint[], remove: TrackPoint[]): TrackPoint[] => {
	const byFrame = new Map<number, TrackPoint>();
	for (const p of keep) {
		byFrame.set(p.frame, p);
	}
	for (const p of remove) {
		if (!byFrame.has(p.frame)) {
			byFrame.set(p.frame, p);
		}
	}
	return Array.from(byFrame.values()).sort((a, b) => a.frame - b.frame);
};

export const isUnknownLabel = (x: string | null | undefined): boolean => {
	return !x || x === 'IND';
};

export const sortIndeterminados = (items: Indeterminados): [string, Indeterminado][] => {
	const soloEntrada = (it: Indeterminado) =>
		!isUnknownLabel(it.labels.in) && isUnknownLabel(it.labels.out);
	return Object.entries(items).sort(
		([, a], [, b]) =>
			Number(soloEntrada(b)) - Number(soloEntrada(a)) ||
			parseInt(a.first_appearance.frame) - parseInt(b.first_appearance.frame)
	);
};

export const groupByFirstAppearance = (
	items: Indeterminados
): Map<number, { trackId: string; bbox: BoundingBox }[]> => {
	const map = new Map<number, { trackId: string; bbox: BoundingBox }[]>();
	for (const [trackId, item] of Object.entries(items)) {
		const frame = parseInt(item.first_appearance.frame);
		if (!map.has(frame)) {
			map.set(frame, []);
		}
		map.get(frame)!.push({ trackId, bbox: item.first_appearance.boundingBox });
	}
	return map;
};

export const mergeIndeterminados = (keep: Indeterminado, remove: Indeterminado): Indeterminado => {
	const pickLabel = (a: string, b: string) => (isUnknownLabel(a) && !isUnknownLabel(b) ? b : a);
	const keepFirst = parseInt(keep.first_appearance.frame);
	const removeFirst = parseInt(remove.first_appearance.frame);
	const keepLast = parseInt(keep.last_appearance.frame);
	const removeLast = parseInt(remove.last_appearance.frame);
	return {
		...keep,
		labels: {
			in: pickLabel(keep.labels.in, remove.labels.in) ?? '',
			out: pickLabel(keep.labels.out, remove.labels.out) ?? ''
		},
		first_appearance: keepFirst <= removeFirst ? keep.first_appearance : remove.first_appearance,
		last_appearance: keepLast >= removeLast ? keep.last_appearance : remove.last_appearance
	};
};

export const getTrackClass = (
	trackId: string,
	determinados: Indeterminados,
	indeterminados: Indeterminados,
	history: History
): string | null => {
	const cls =
		determinados[trackId]?.class || indeterminados[trackId]?.class || history[trackId]?.class;
	return cls ? String(cls) : null;
};

export const getVehicleName = (key: string): string => {
	if (!key) {
		return 'N/A';
	}
	return key.charAt(0).toUpperCase() + key.slice(1).toLowerCase().replaceAll(/_/g, ' ');
};

export const getVehicleTypes = (rutas: Rutas, indeterminados: Indeterminados): string[] => {
	if (Object.keys(rutas).length === 0) {
		return [];
	}
	const types = new Set<string>();
	for (const salidas of Object.values(rutas)) {
		for (const conteo of Object.values(salidas)) {
			Object.keys(conteo).forEach((v) => types.add(v));
		}
	}
	Object.values(indeterminados).forEach((item) => types.add(item.class));
	return Array.from(types).sort();
};

export const getZoneIds = (rutas: Rutas): string[] => {
	const zones = new Set<string>(Object.keys(rutas));
	Object.values(rutas).forEach((salidas) => Object.keys(salidas).forEach((id) => zones.add(id)));
	return Array.from(zones).sort();
};

export const incrementarRuta = (
	rutas: Rutas,
	entrada: string,
	salida: string,
	vehiculo: string,
	vehicleTypes: string[]
) => {
	if (!rutas[entrada]) {
		rutas[entrada] = {};
	}
	if (!rutas[entrada][salida]) {
		rutas[entrada][salida] = {};
	}
	const conteo = rutas[entrada][salida];
	if (conteo[vehiculo] === undefined) {
		for (const v of vehicleTypes) {
			conteo[v] ??= 0;
		}
	}
	conteo[vehiculo] = (conteo[vehiculo] ?? 0) + 1;
};

const buildTabla = (
	prefijo: string,
	ids: string[],
	vehicleTypes: string[],
	getConteo: (id: string, vehiculo: string) => number
): Tabla => {
	const columnas = ids.map((id) => `${prefijo} ${id}`);
	const total: FilaTabla = { tipo: 'Total', ...Object.fromEntries(columnas.map((c) => [c, 0])) };
	const datos = vehicleTypes.map((vehiculo) => {
		const fila: FilaTabla = { tipo: getVehicleName(vehiculo), __key: vehiculo };
		ids.forEach((id, i) => {
			const conteo = getConteo(id, vehiculo);
			fila[columnas[i]] = conteo;
			(total[columnas[i]] as number) += conteo;
		});
		return fila;
	});
	return { columnas, datos, total };
};

export const buildTablaEntradas = (rutas: Rutas, vehicleTypes: string[]): Tabla => {
	const entradasIds = Object.keys(rutas).sort();
	return buildTabla('Entrada', entradasIds, vehicleTypes, (entradaId, vehiculo) =>
		Object.values(rutas[entradaId] ?? {}).reduce((sum, conteo) => sum + (conteo[vehiculo] ?? 0), 0)
	);
};

export const buildTablaSalidas = (rutas: Rutas, vehicleTypes: string[]): Tabla => {
	const salidasIds = [...new Set(Object.values(rutas).flatMap(Object.keys))].sort();
	return buildTabla('Salida', salidasIds, vehicleTypes, (salidaId, vehiculo) =>
		Object.values(rutas).reduce((sum, salidas) => sum + (salidas[salidaId]?.[vehiculo] ?? 0), 0)
	);
};

export const buildTablasPorEntrada = (
	rutas: Rutas,
	vehicleTypes: string[]
): (Tabla & { nombreEntrada: string })[] =>
	Object.keys(rutas)
		.sort()
		.map((entradaId) => ({
			nombreEntrada: `Desde Entrada ${entradaId}`,
			...buildTabla(
				'Salida',
				Object.keys(rutas[entradaId]).sort(),
				vehicleTypes,
				(salidaId, vehiculo) => rutas[entradaId][salidaId][vehiculo] ?? 0
			)
		}));

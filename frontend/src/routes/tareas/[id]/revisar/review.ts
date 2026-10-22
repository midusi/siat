import { apiError } from '$lib/services/errors';
import { apiFetch } from '$lib/api';

export type Appearance = { frame: string; boundingBox: BoundingBox };
export type AppearingBox = { trackId: string; bbox: BoundingBox };
export type BoundingBox = [string, string, string, string];
export type Bounds = { width: number; height: number };
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
	labels: Labels;
};
export type IndeterminadoField = 'class' | 'in' | 'out';
export type Indeterminados = { [trackId: string]: Indeterminado };
type Intersection = Point & { t: number };
export type Labels = { in: string; out: string };
type ObjHistory = Record<string, Array<ObjHistoryEntry>>;
type ObjHistoryEntry = { act_frame: number; box: Box };
export type Point = { x: number; y: number };
type RawIndeterminado = Omit<Indeterminado, 'labels'> & {
	labels: Labels | [string, string];
};
type RawIndeterminados = Record<string, RawIndeterminado>;
type RawTaskReview = {
	data_obj_history_url?: string;
	dataObjHistoryUrl?: string;
	determinados?: RawIndeterminados;
	excludedZones?: unknown;
	history?: History;
	historyUrl?: string;
	indeterminados?: RawIndeterminados;
	roadsIn?: unknown;
	roadsOut?: unknown;
	rutas?: Rutas;
	videoFps: number | string;
	videoHeight: number | string;
	videoPath?: string;
	videoWidth: number | string;
};
export type Rect = { x: number; y: number; width: number; height: number };
export type RoadPoly = { id: number; name: string; direction: string; polygon: Array<Vertex> };
export type Rutas = { [entrada: string]: { [salida: string]: ConteoVehiculos } };
export type Scale = { x: number; y: number };
export type SelectOption = { value: string; label: string };
export type Tabla = { columnas: Array<string>; datos: Array<FilaTabla>; total: FilaTabla };
export type TablaPorEntrada = Tabla & { nombreEntrada: string };
export type TaskReview = {
	videoPath: string;
	videoWidth: number;
	videoHeight: number;
	videoFps: number;
	roadsIn: Array<RoadPoly>;
	roadsOut: Array<RoadPoly>;
	excludedZones: Array<Array<Vertex>>;
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
	trackHistory: TrackHistory;
};
export type TrackHistory = Map<string, Array<TrackPoint>>;
export type TrackPoint = { frame: number; box: Box };
export type Vertex = [number, number];

export const FADE_OUT_DURATION_SECONDS: number = 1.0;
export const OPACITY_TRANSITION_MS: number = 500;
const TASK_API: string = '/task';

const normalizeLabels = (items: RawIndeterminados | null | undefined): Indeterminados => {
	const out: Indeterminados = {};
	for (const [id, it] of Object.entries(items ?? {})) {
		const labels: Labels = Array.isArray(it.labels)
			? { in: it.labels[0] ?? '', out: it.labels[1] ?? '' }
			: it.labels;
		out[id] = { ...it, labels };
	}
	return out;
};

const asArray = <T>(value: unknown): Array<T> => (Array.isArray(value) ? value : []);

export const fetchTaskReview = async (taskId: string): Promise<TaskReview> => {
	const res: Response = await apiFetch(`${TASK_API}/${taskId}`);
	if (!res.ok) {
		throw await apiError(res, 'No se pudieron obtener los datos de la tarea');
	}
	const data: RawTaskReview = await res.json();
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

export const fetchTrackHistory = async (url: string): Promise<TrackHistory> => {
	const res: Response = await fetch(`${url}${url.includes('?') ? '&' : '?'}_ts=${Date.now()}`);
	if (!res.ok) {
		throw new Error('Error al obtener data_obj_history.json');
	}
	const json: ObjHistory = await res.json();
	const trackMap: TrackHistory = new Map();
	for (const [trackId, entries] of Object.entries(json)) {
		const points: Array<TrackPoint> = entries.map((e) => ({
			frame: Number(e.act_frame),
			box: e.box
		}));
		trackMap.set(
			trackId,
			points.sort((a, b) => a.frame - b.frame)
		);
	}
	return trackMap;
};

const serializeTrackHistory = (trackMap: TrackHistory): ObjHistory => {
	const out: ObjHistory = {};
	for (const [trackId, points] of trackMap.entries()) {
		out[trackId] = points
			.slice()
			.sort((a, b) => a.frame - b.frame)
			.map((p) => ({ act_frame: p.frame, box: p.box }));
	}
	return out;
};

export const updateTaskReview = async (
	taskId: string,
	changes: TaskReviewChanges
): Promise<void> => {
	const res: Response = await apiFetch(`${TASK_API}/${taskId}/update-data`, {
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
	const span: number = Math.max(0, last - first);
	const t: number = Math.min(Math.max(timeSec, 0), dur);
	const f: number = first + (span > 0 ? Math.round((t / dur) * span) : 0);
	return Math.max(first, Math.min(f, last));
};

export const frameToTime = (frame: number, range: FrameRange | null, fps: number): number => {
	if (!range) {
		return fps > 0 ? frame / fps : 0;
	}
	const { dur, first, last } = range;
	const span: number = Math.max(0, last - first);
	const clamped: number = Math.max(first, Math.min(frame, last));
	const t: number = span > 0 ? ((clamped - first) / span) * dur : 0;
	return Math.max(0, Math.min(t, dur));
};

export const isFrameWithinTrack = (points: Array<TrackPoint>, frame: number): boolean => {
	if (!points.length) {
		return false;
	}
	return frame >= points[0].frame && frame <= points[points.length - 1].frame;
};

export const fadeBoxes = (
	boxes: Array<DisplayableBBox>,
	clock: number,
	nowMs: number
): Array<DisplayableBBox> => {
	const out: Array<DisplayableBBox> = [];
	for (const box of boxes) {
		const opacity: number = Math.max(
			0,
			Math.min(1, (box.hideAtTime - clock) / FADE_OUT_DURATION_SECONDS)
		);
		if (opacity > 0) {
			const unchanged: boolean = opacity === box.opacity && !box.fadeRemoveAtMs;
			out.push(unchanged ? box : { ...box, opacity, fadeRemoveAtMs: undefined });
			continue;
		}
		const removeAt: number = box.fadeRemoveAtMs ?? nowMs + OPACITY_TRANSITION_MS;
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

export const toScaledClampedRect = (box: Box, scale: Scale, bounds: Bounds): Rect | null => {
	const [x1, y1, x2, y2] = box;
	let left: number = x1 * scale.x;
	let top: number = y1 * scale.y;
	let width: number = (x2 - x1) * scale.x;
	let height: number = (y2 - y1) * scale.y;
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

export const scalePolygon = (poly: Array<Vertex>, scale: Scale): string => {
	return poly.map(([x, y]) => `${x * scale.x},${y * scale.y}`).join(' ');
};

const segmentRectIntersections = (p1: Point, p2: Point, rect: Rect): Array<Intersection> => {
	const xL: number = rect.x;
	const xR: number = rect.x + rect.width;
	const yT: number = rect.y;
	const yB: number = rect.y + rect.height;
	const dx: number = p2.x - p1.x;
	const dy: number = p2.y - p1.y;
	const res: Array<Intersection> = [];
	const add = (t: number, x: number, y: number): void => {
		if (t >= 0 && t <= 1) {
			res.push({ t, x, y });
		}
	};
	if (dx !== 0) {
		for (const edgeX of [xL, xR]) {
			const t: number = (edgeX - p1.x) / dx;
			const y: number = p1.y + t * dy;
			if (y >= yT && y <= yB) {
				add(t, edgeX, y);
			}
		}
	}
	if (dy !== 0) {
		for (const edgeY of [yT, yB]) {
			const t: number = (edgeY - p1.y) / dy;
			const x: number = p1.x + t * dx;
			if (x >= xL && x <= xR) {
				add(t, x, edgeY);
			}
		}
	}
	return res.sort((a, b) => a.t - b.t);
};

const isInsideRect = (p: Point, rect: Rect): boolean =>
	p.x >= rect.x && p.x <= rect.x + rect.width && p.y >= rect.y && p.y <= rect.y + rect.height;

export const clipPolyline = (pts: Array<Point>, rect: Rect | null): Array<Array<Point>> => {
	if (!rect) {
		return pts.length > 1 ? [pts] : [];
	}
	const out: Array<Array<Point>> = [];
	let seg: Array<Point> = [];
	for (let i = 1; i < pts.length; i++) {
		const a: Point = pts[i - 1];
		const b: Point = pts[i];
		const inA: boolean = isInsideRect(a, rect);
		const inB: boolean = isInsideRect(b, rect);
		if (!inA && !inB) {
			const ints: Array<Intersection> = segmentRectIntersections(a, b, rect);
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
			const first: Intersection | undefined = segmentRectIntersections(a, b, rect)[0];
			seg = first ? [{ x: first.x, y: first.y }, b] : [b];
		} else if (!inA && inB) {
			const last: Intersection | undefined = segmentRectIntersections(a, b, rect).at(-1);
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

export const buildFrameMap = (trackMap: TrackHistory): Map<number, Array<GeneralBBox>> => {
	const frameMap: Map<number, Array<GeneralBBox>> = new Map();
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

export const mergeTrackPoints = (
	keep: Array<TrackPoint>,
	remove: Array<TrackPoint>
): Array<TrackPoint> => {
	const byFrame: Map<number, TrackPoint> = new Map();
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

export const sortIndeterminados = (items: Indeterminados): Array<[string, Indeterminado]> => {
	const soloEntrada = (it: Indeterminado): boolean =>
		!isUnknownLabel(it.labels.in) && isUnknownLabel(it.labels.out);
	return Object.entries(items).sort(
		([, a], [, b]) =>
			Number(soloEntrada(b)) - Number(soloEntrada(a)) ||
			parseInt(a.first_appearance.frame) - parseInt(b.first_appearance.frame)
	);
};

export const groupByFirstAppearance = (items: Indeterminados): Map<number, Array<AppearingBox>> => {
	const map: Map<number, Array<AppearingBox>> = new Map();
	for (const [trackId, item] of Object.entries(items)) {
		const frame: number = parseInt(item.first_appearance.frame);
		if (!map.has(frame)) {
			map.set(frame, []);
		}
		map.get(frame)!.push({ trackId, bbox: item.first_appearance.boundingBox });
	}
	return map;
};

export const mergeIndeterminados = (keep: Indeterminado, remove: Indeterminado): Indeterminado => {
	const pickLabel = (a: string, b: string): string =>
		isUnknownLabel(a) && !isUnknownLabel(b) ? b : a;
	const keepFirst: number = parseInt(keep.first_appearance.frame);
	const removeFirst: number = parseInt(remove.first_appearance.frame);
	const keepLast: number = parseInt(keep.last_appearance.frame);
	const removeLast: number = parseInt(remove.last_appearance.frame);
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
	const cls: string | undefined =
		determinados[trackId]?.class || indeterminados[trackId]?.class || history[trackId]?.class;
	return cls ? String(cls) : null;
};

export const getVehicleName = (key: string): string => {
	if (!key) {
		return 'N/A';
	}
	return key.charAt(0).toUpperCase() + key.slice(1).toLowerCase().replaceAll(/_/g, ' ');
};

export const getVehicleTypes = (rutas: Rutas, indeterminados: Indeterminados): Array<string> => {
	if (Object.keys(rutas).length === 0) {
		return [];
	}
	const types: Set<string> = new Set();
	for (const salidas of Object.values(rutas)) {
		for (const conteo of Object.values(salidas)) {
			Object.keys(conteo).forEach((v) => types.add(v));
		}
	}
	Object.values(indeterminados).forEach((item) => types.add(item.class));
	return Array.from(types).sort();
};

export const getZoneIds = (rutas: Rutas): Array<string> => {
	const zones: Set<string> = new Set(Object.keys(rutas));
	Object.values(rutas).forEach((salidas) => Object.keys(salidas).forEach((id) => zones.add(id)));
	return Array.from(zones).sort();
};

export const incrementarRuta = (
	rutas: Rutas,
	entrada: string,
	salida: string,
	vehiculo: string,
	vehicleTypes: Array<string>
): void => {
	if (!rutas[entrada]) {
		rutas[entrada] = {};
	}
	if (!rutas[entrada][salida]) {
		rutas[entrada][salida] = {};
	}
	const conteo: ConteoVehiculos = rutas[entrada][salida];
	if (conteo[vehiculo] === undefined) {
		for (const v of vehicleTypes) {
			conteo[v] ??= 0;
		}
	}
	conteo[vehiculo] = (conteo[vehiculo] ?? 0) + 1;
};

const buildTabla = (
	prefijo: string,
	ids: Array<string>,
	vehicleTypes: Array<string>,
	getConteo: (id: string, vehiculo: string) => number
): Tabla => {
	const columnas: Array<string> = ids.map((id) => `${prefijo} ${id}`);
	const total: FilaTabla = { tipo: 'Total', ...Object.fromEntries(columnas.map((c) => [c, 0])) };
	const datos: Array<FilaTabla> = vehicleTypes.map((vehiculo) => {
		const fila: FilaTabla = { tipo: getVehicleName(vehiculo), __key: vehiculo };
		ids.forEach((id, i) => {
			const conteo: number = getConteo(id, vehiculo);
			fila[columnas[i]] = conteo;
			(total[columnas[i]] as number) += conteo;
		});
		return fila;
	});
	return { columnas, datos, total };
};

export const buildTablaEntradas = (rutas: Rutas, vehicleTypes: Array<string>): Tabla => {
	const entradasIds: Array<string> = Object.keys(rutas).sort();
	return buildTabla('Entrada', entradasIds, vehicleTypes, (entradaId, vehiculo) =>
		Object.values(rutas[entradaId] ?? {}).reduce((sum, conteo) => sum + (conteo[vehiculo] ?? 0), 0)
	);
};

export const buildTablaSalidas = (rutas: Rutas, vehicleTypes: Array<string>): Tabla => {
	const salidasIds: Array<string> = [...new Set(Object.values(rutas).flatMap(Object.keys))].sort();
	return buildTabla('Salida', salidasIds, vehicleTypes, (salidaId, vehiculo) =>
		Object.values(rutas).reduce((sum, salidas) => sum + (salidas[salidaId]?.[vehiculo] ?? 0), 0)
	);
};

export const buildTablasPorEntrada = (
	rutas: Rutas,
	vehicleTypes: Array<string>
): Array<TablaPorEntrada> =>
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

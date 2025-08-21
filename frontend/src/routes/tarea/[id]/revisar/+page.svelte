<script lang="ts">
	import { onMount } from 'svelte';
	import { apiFetch } from '$lib/api';
	import { showSuccess, showError } from '$lib/toast';
	import Spinner from '$lib/components/Spinner.svelte';
	import GlassSelect from '$lib/components/GlassSelect.svelte';

	// --- Props y estado inicial ---
	let { data } = $props();
	let loading = $state(true);
	let error = $state<string | null>(null);

	// --- Referencias a elementos del DOM ---
	let videoElement = $state<HTMLVideoElement | null>(null);
	let videoHeightPx = $state(0);

	// --- Estado para bboxes generales ---
	type GeneralBBox = { id: string; box: [number, number, number, number] };
	let generalBBoxesByFrame = $state<Map<number, GeneralBBox[]>>(new Map());
	let generalDisplayBBoxes = $state<GeneralBBox[]>([]);
	let generalReady = $state(false); // Indica si el JSON general está listo

	// Historial por track para dibujar recorridos desde data_obj_history
	type TrackPoint = { frame: number; box: [number, number, number, number] };
	let generalTrackHistory = $state<Map<string, TrackPoint[]>>(new Map());

	// Estado de selección de vehículo y sus recorridos pasado/futuro
	let selectedTrackId = $state<string | null>(null);
	let routePastPoints = $state<{ x: number; y: number }[]>([]);
	let routeFuturePoints = $state<{ x: number; y: number }[]>([]);
	let routeAllPoints = $state<{ x: number; y: number }[]>([]);
	let routePastSegments = $state<{ x: number; y: number }[][]>([]);
	let routeFutureSegments = $state<{ x: number; y: number }[][]>([]);
	// Clave para re-montar rutas y reiniciar animación al seleccionar
	let routeAnimateKey = $state(0);
	// Flag y timer para animación rápida y fallback si falla la animación CSS
	let routeAnimating = $state(false);
	let routeAnimTimer: any = null;
	// Rect del bbox seleccionado en el frame actual (para ocultar ruta dentro del bbox)
	let selectedBoxRect = $state<{ x: number; y: number; width: number; height: number } | null>(
		null
	);

	// Estado para mostrar ruta al hacer click
	let selectedRoute: { id: string; label: string } | null = $state(null);

	// Control de loop para resetear overlays al reiniciar el video automáticamente
	let lastVideoTime = 0;

	// --- Definiciones de Tipos ---
	type Vehiculo = string;
	type ConteoVehiculos = { [key: Vehiculo]: number };
	type Rutas = { [entrada: string]: { [salida: string]: ConteoVehiculos } };
	type History = {
		[trackId: string]: { frame: string; boundingBox: BoundingBox; class: Vehiculo };
	};
	type BoundingBox = [string, string, string, string];
	type Indeterminado = {
		first_appearance: {
			frame: string;
			boundingBox: BoundingBox;
		};
		last_appearance: {
			frame: string;
			boundingBox: BoundingBox;
		};
		class: Vehiculo;
		// boundingBox: BoundingBox;
		labels: [string, string];
	};
	type Indeterminados = { [trackId: string]: Indeterminado };
	type FilaTabla = { tipo: string; [key: string]: string | number };
	// CAMBIO 1: Añadimos 'opacity' al tipo de la BBox que se va a renderizar.
	type DisplayableBBox = { id: string; bbox: BoundingBox; hideAtTime: number; opacity: number };

	// --- Estado reactivo ---
	let videoPath = $state('');
	let videoWidth = $state(0);
	let videoHeight = $state(0);
	let videoFps = $state(0);
	let videoDuration = $state(0);
	let rutas = $state<Rutas>({});
	let indeterminados = $state<Indeterminados>({});
	let determinados = $state<Record<string, any>>({});
	let determinadosByTrack = $derived.by(() => new Map(Object.entries(determinados)));
	type SortedIndeterminado = [string, Indeterminado];
	let sortedIndeterminados = $state<SortedIndeterminado[]>([]);
	let videoScale = $state({ x: 1, y: 1 });
	let savingById = $state<Record<string, boolean>>({});
	let history = $state<History>({});
	// Rango de frames disponibles (para mapear tiempo->frame sin depender estrictamente de FPS)
	let dataFrameFirst = $state<number | null>(null);
	let dataFrameLast = $state<number | null>(null);

	function computeCurrentFrameFromTime(timeSec: number): number {
		const dur = videoElement?.duration ?? videoDuration ?? 0;
		if (dur > 0 && dataFrameFirst !== null && dataFrameLast !== null) {
			const t = Math.min(Math.max(timeSec, 0), dur);
			const span = Math.max(0, dataFrameLast - dataFrameFirst);
			const f = dataFrameFirst + (span > 0 ? Math.round((t / dur) * span) : 0);
			return Math.max(dataFrameFirst, Math.min(f, dataFrameLast));
		}
		return Math.floor(timeSec * (videoFps || 0));
	}

	function computeTimeFromFrame(frame: number): number {
		const dur = videoElement?.duration ?? videoDuration ?? 0;
		if (dur > 0 && dataFrameFirst !== null && dataFrameLast !== null) {
			const span = Math.max(0, dataFrameLast - dataFrameFirst);
			const clamped = Math.max(dataFrameFirst, Math.min(frame, dataFrameLast));
			const t = span > 0 ? ((clamped - dataFrameFirst) / span) * dur : 0;
			return Math.max(0, Math.min(t, dur));
		}
		return videoFps > 0 ? frame / videoFps : 0;
	}
	// --- ESTADOS DE BBOX Y ANIMACIÓN ---
	let activeBoundingBox = $state<BoundingBox | null>(null);
	let playbackBoundingBoxes = $state<DisplayableBBox[]>([]);

	// ID del bucle de animación para poder cancelarlo
	let animationFrameId: number | null = null;
	// Para no volver a procesar el mismo frame en el bucle
	let lastProcessedFrame = -1;
	// CAMBIO 2: Renombramos la constante para que sea más claro que es la duración del desvanecimiento.
	const FADE_OUT_DURATION_SECONDS = 1.0;

	// --- ESTRUCTURA DE DATOS OPTIMIZADA POR FRAME ---
	let indeterminadosByFrame = $derived.by(() => {
		const map = new Map<number, { trackId: string; bbox: BoundingBox }[]>();
		for (const [trackId, item] of Object.entries(indeterminados)) {
			const frame = parseInt(item.first_appearance.frame);
			if (!map.has(frame)) {
				map.set(frame, []);
			}
			map.get(frame)!.push({ trackId, bbox: item.first_appearance.boundingBox });
		}
		return map;
	});

	// --- LÓGICA DEL BUCLE DE ANIMACIÓN (MODIFICADA PARA DESVANECIMIENTO Y GENERAL BBOXES) ---
	function animationLoop() {
		if (!videoElement || videoElement.paused) {
			animationFrameId = null;
			return;
		}

		const currentTime = videoElement.currentTime;
		const currentFrame = computeCurrentFrameFromTime(currentTime);

		// Detectar loop (el tiempo se resetea de fin a inicio sin pausa)
		if (currentTime + 0.05 < lastVideoTime) {
			// Resetear estados dependientes del tiempo/frames
			lastProcessedFrame = -1;
			playbackBoundingBoxes = [];
			console.log('Video looped: reset de estados de animación');
		}

		// --- Actualizar bboxes generales ---
		generalDisplayBBoxes = generalBBoxesByFrame.get(currentFrame) ?? [];
		// Actualizar rectángulo del bbox seleccionado (si está en el frame actual)
		if (selectedTrackId && videoElement) {
			const sel = generalDisplayBBoxes.find((b) => b.id === selectedTrackId);
			if (sel) {
				const [x1, y1, x2, y2] = sel.box;
				let left = x1 * videoScale.x;
				let top = y1 * videoScale.y;
				let width = (x2 - x1) * videoScale.x;
				let height = (y2 - y1) * videoScale.y;
				const vw = videoElement.clientWidth,
					vh = videoElement.clientHeight;
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
				if (left + width > vw) {
					width = vw - left;
				}
				if (top + height > vh) {
					height = vh - top;
				}
				if (width > 0 && height > 0) selectedBoxRect = { x: left, y: top, width, height };
				else selectedBoxRect = null;
			} else {
				selectedBoxRect = null;
			}
		} else {
			selectedBoxRect = null;
		}
		// Ahora que tenemos el rect actualizado, calcular rutas/segmentos
		if (selectedTrackId) updateSelectedTrackRoute(currentFrame);
		// Si no hay ningún vehículo en pantalla, deseleccionar y limpiar rutas
		if (generalDisplayBBoxes.length === 0 && selectedTrackId) {
			selectedTrackId = null;
			routePastPoints = [];
			routeFuturePoints = [];
			routeAllPoints = [];
		}

		// --- Indeterminados (con desvanecimiento, como antes) ---
		if (playbackBoundingBoxes.length > 0) {
			playbackBoundingBoxes = playbackBoundingBoxes
				.map((box) => {
					const timeUntilHidden = box.hideAtTime - currentTime;
					// Calculamos la nueva opacidad. Será un valor entre 0 y 1.
					const newOpacity = Math.max(
						0,
						Math.min(1.0, timeUntilHidden / FADE_OUT_DURATION_SECONDS)
					);
					return { ...box, opacity: newOpacity };
				})
				.filter((box) => box.opacity > 0); // Solo mantenemos las que son visibles.
		}

		// Añadir nuevas bboxes indeterminadas si hemos avanzado a un nuevo frame
		if (currentFrame > lastProcessedFrame) {
			for (let frame = lastProcessedFrame + 1; frame <= currentFrame; frame++) {
				const bboxesInfo = indeterminadosByFrame.get(frame);
				if (bboxesInfo) {
					const newBoxes = bboxesInfo.map((info) => ({
						id: info.trackId,
						bbox: info.bbox,
						hideAtTime: computeTimeFromFrame(frame) + FADE_OUT_DURATION_SECONDS,
						opacity: 1.0 // Empiezan con opacidad total
					}));
					playbackBoundingBoxes = [...playbackBoundingBoxes, ...newBoxes];
				}
			}
		}

		lastProcessedFrame = currentFrame;
		lastVideoTime = currentTime;
		animationFrameId = requestAnimationFrame(animationLoop);
	}

	// --- FUNCIONES DE CONTROL DEL VIDEO ---
	function startAnimationLoop() {
		if (animationFrameId === null) {
			activeBoundingBox = null;
			activeIndeterminateId = null;
			playbackBoundingBoxes = [];

			// CAMBIO CLAVE:
			// En lugar de reiniciar siempre a -1, establecemos el último frame procesado
			// justo antes de la posición actual de reproducción. Esto evita que el bucle
			// "repase" la historia del video que fue omitida por una búsqueda (seek).
			if (videoElement) {
				lastProcessedFrame = computeCurrentFrameFromTime(videoElement.currentTime) - 1;
			} else {
				lastProcessedFrame = -1;
			}

			animationFrameId = requestAnimationFrame(animationLoop);
		}
	}

	function stopAnimationLoop() {
		if (animationFrameId !== null) {
			cancelAnimationFrame(animationFrameId);
			animationFrameId = null;
		}
	}

	// CAMBIO 4: La BBox manual también debe tener una propiedad 'opacity' para ser consistente.
	let displayBoundingBoxes = $derived.by(() => {
		if (activeBoundingBox) {
			return [{ id: 'active-manual', bbox: activeBoundingBox, hideAtTime: Infinity, opacity: 1.0 }];
		}
		return playbackBoundingBoxes;
	});

	// --- Lógica de Interacción ---
	// IDs de las tarjetas que corresponden a BBoxes visibles en el video
	let liveIndeterminateIds = $derived.by(() => {
		// Usamos un Set para búsquedas ultra-rápidas (O(1)) en el template
		return new Set(playbackBoundingBoxes.map((box) => box.id));
	});
	let activeIndeterminateId = $state<string | null>(null);
	function handleIndeterminateClick(trackId: string) {
		activeIndeterminateId = trackId;
		if (!videoElement) return;
		const item = indeterminados[trackId];
		if (!item) return;

		stopAnimationLoop();
		videoElement.pause();

		const timeInSeconds = computeTimeFromFrame(parseInt(item.first_appearance.frame));
		videoElement.currentTime = timeInSeconds;
		activeBoundingBox = item.first_appearance.boundingBox;
	}

	// --- El resto del código permanece casi igual ---
	function updateVideoDimensions() {
		if (videoElement) {
			videoHeightPx = videoElement.clientHeight;
			if (videoWidth > 0 && videoHeight > 0) {
				videoScale.x = videoElement.clientWidth / videoWidth;
				videoScale.y = videoElement.clientHeight / videoHeight;
				if (selectedTrackId && videoElement) {
					const currentFrame = computeCurrentFrameFromTime(videoElement.currentTime);
					updateSelectedTrackRoute(currentFrame);
				}
			}
		}
	}
	// CAMBIO 5: La función ahora recibe el objeto `DisplayableBBox` completo.
	function calculateBoxStyle(box: DisplayableBBox): string {
		if (!videoElement) return 'display: none;';

		const { bbox, opacity } = box;
		const [x1_str, y1_str, x2_str, y2_str] = bbox;
		const x1 = parseFloat(x1_str),
			y1 = parseFloat(y1_str),
			x2 = parseFloat(x2_str),
			y2 = parseFloat(y2_str);

		let left = x1 * videoScale.x;
		let top = y1 * videoScale.y;
		let width = (x2 - x1) * videoScale.x;
		let height = (y2 - y1) * videoScale.y;

		const videoRenderedWidth = videoElement.clientWidth,
			videoRenderedHeight = videoElement.clientHeight;
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
		if (left + width > videoRenderedWidth) {
			width = videoRenderedWidth - left;
		}
		if (top + height > videoRenderedHeight) {
			height = videoRenderedHeight - top;
		}
		if (width <= 0 || height <= 0) return 'display: none;';

		// Añadimos la opacidad al estilo dinámico.
		return `position: absolute; left: ${left}px; top: ${top}px; width: ${width}px; height: ${height}px; opacity: ${opacity};`;
	}
	// --- BBoxes generales a mostrar (sin fade, sin ID) ---
	function calculateGeneralBoxStyle(box: GeneralBBox): string {
		if (!videoElement) return 'display: none;';
		const [x1, y1, x2, y2] = box.box;
		let left = x1 * videoScale.x;
		let top = y1 * videoScale.y;
		let width = (x2 - x1) * videoScale.x;
		let height = (y2 - y1) * videoScale.y;
		const videoRenderedWidth = videoElement.clientWidth,
			videoRenderedHeight = videoElement.clientHeight;
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
		if (left + width > videoRenderedWidth) {
			width = videoRenderedWidth - left;
		}
		if (top + height > videoRenderedHeight) {
			height = videoRenderedHeight - top;
		}
		if (width <= 0 || height <= 0) return 'display: none;';

		// Rectángulo completo, borde blanco; si está seleccionado, aplicar glow como los indeterminados
		const isSelected = selectedTrackId === box.id;
		const glow = isSelected
			? 'box-shadow: 0 0 5px rgba(255,255,255,0.8), 0 0 10px rgba(255,255,255,0.6), 0 0 20px rgba(255,255,255,0.4);'
			: 'box-shadow: none;';
		return `position: absolute; left: ${left}px; top: ${top}px; width: ${width}px; height: ${height}px; border: 2px solid #ffffff; ${glow} pointer-events: auto; z-index: 12; cursor: pointer;`;
	}

	function calculateRoutePillStyle(box: GeneralBBox): string {
		if (!videoElement) return 'display:none;';
		const [x1, y1, x2, y2] = box.box;
		let left = x1 * videoScale.x + 4;
		let top = y1 * videoScale.y - 22; // encima del bbox
		const videoRenderedWidth = videoElement.clientWidth,
			videoRenderedHeight = videoElement.clientHeight;
		if (top < 0) top = y1 * videoScale.y + 4; // si no hay espacio arriba, poner dentro
		if (left < 0) left = 0;
		if (left > videoRenderedWidth - 120) left = videoRenderedWidth - 120;
		return `position:absolute; left:${left}px; top:${top}px; z-index:13; pointer-events:none;`;
	}

	function showRouteFor(box: GeneralBBox) {
		// Usar el historial del track (data_obj_history) para mostrar recorrido pasado/futuro y la ruta completa
		selectedTrackId = box.id;
		const currentFrame = videoElement ? computeCurrentFrameFromTime(videoElement.currentTime) : 0;
		// Calcular inmediatamente el rectángulo del bbox seleccionado (incluso si el video está en pausa)
		if (videoElement) {
			const [x1, y1, x2, y2] = box.box;
			let left = x1 * videoScale.x;
			let top = y1 * videoScale.y;
			let width = (x2 - x1) * videoScale.x;
			let height = (y2 - y1) * videoScale.y;
			const vw = videoElement.clientWidth,
				vh = videoElement.clientHeight;
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
			if (left + width > vw) {
				width = vw - left;
			}
			if (top + height > vh) {
				height = vh - top;
			}
			selectedBoxRect = width > 0 && height > 0 ? { x: left, y: top, width, height } : null;
		}
		const points = generalTrackHistory.get(box.id) || [];
		// Calcular la ruta completa con todos los puntos del track
		const toXY = (p: TrackPoint) => {
			const [x1, y1, x2, y2] = p.box;
			return { x: ((x1 + x2) / 2) * videoScale.x, y: ((y1 + y2) / 2) * videoScale.y };
		};
		routeAllPoints = points.map(toXY);
		console.log('showRouteFor select', box.id, {
			totalPoints: points.length,
			currentFrame,
			selectedBoxRect
		});
		updateSelectedTrackRoute(currentFrame);
		console.log('after updateSelectedTrackRoute', {
			pastSegs: routePastSegments.length,
			futureSegs: routeFutureSegments.length,
			pastPts: routePastPoints.length,
			futurePts: routeFuturePoints.length
		});
		// Disparar animación rápida (activar antes del remount para que las polylines nazcan animadas)
		if (routeAnimTimer) clearTimeout(routeAnimTimer);
		routeAnimating = true;
		routeAnimTimer = setTimeout(() => (routeAnimating = false), 320);
		// Incrementar clave para re-montar SVG y disparar animación
		routeAnimateKey++;
	}

	function updateSelectedTrackRoute(currentFrame: number) {
		if (!selectedTrackId) return;
		const trackPoints = generalTrackHistory.get(selectedTrackId) || [];
		if (!videoElement || trackPoints.length === 0) {
			routePastPoints = [];
			routeFuturePoints = [];
			routeAllPoints = [];
			routePastSegments = [];
			routeFutureSegments = [];
			return;
		}
		console.log('updateSelectedTrackRoute:start', {
			selectedTrackId,
			currentFrame,
			trackPoints: trackPoints.length,
			selectedBoxRect
		});
		const past = trackPoints.filter((p) => p.frame <= currentFrame);
		const future = trackPoints.filter((p) => p.frame > currentFrame);
		const toXY = (p: TrackPoint) => {
			const [x1, y1, x2, y2] = p.box;
			return { x: ((x1 + x2) / 2) * videoScale.x, y: ((y1 + y2) / 2) * videoScale.y };
		};
		// Trayectorias en orden cronológico
		const pastPts = past.map(toXY);
		const futurePts = future.map(toXY);
		// Guardar arrays base (pueden usarse para otras UI)
		routePastPoints = [...pastPts].reverse();
		routeFuturePoints = futurePts;

		// Funciones auxiliares para recortar en el borde del bbox (cero separación)
		const pad = 0;
		const rect = selectedBoxRect
			? {
					xL: selectedBoxRect.x - pad,
					xR: selectedBoxRect.x + selectedBoxRect.width + pad,
					yT: selectedBoxRect.y - pad,
					yB: selectedBoxRect.y + selectedBoxRect.height + pad
				}
			: null;
		const isInside = (p: { x: number; y: number }) =>
			rect ? p.x >= rect.xL && p.x <= rect.xR && p.y >= rect.yT && p.y <= rect.yB : false;
		const segmentRectIntersections = (
			p1: { x: number; y: number },
			p2: { x: number; y: number }
		) => {
			if (!rect) return [] as { t: number; x: number; y: number }[];
			const res: { t: number; x: number; y: number }[] = [];
			const dx = p2.x - p1.x,
				dy = p2.y - p1.y;
			// Evitar divisiones por cero
			const add = (t: number, x: number, y: number) => {
				if (t >= 0 && t <= 1) res.push({ t, x, y });
			};
			if (dx !== 0) {
				let t = (rect.xL - p1.x) / dx;
				let y = p1.y + t * dy;
				if (y >= rect.yT && y <= rect.yB) add(t, rect.xL, y);
				t = (rect.xR - p1.x) / dx;
				y = p1.y + t * dy;
				if (y >= rect.yT && y <= rect.yB) add(t, rect.xR, y);
			}
			if (dy !== 0) {
				let t = (rect.yT - p1.y) / dy;
				let x = p1.x + t * dx;
				if (x >= rect.xL && x <= rect.xR) add(t, x, rect.yT);
				t = (rect.yB - p1.y) / dy;
				x = p1.x + t * dx;
				if (x >= rect.xL && x <= rect.xR) add(t, x, rect.yB);
			}
			// Ordenar por t
			res.sort((a, b) => a.t - b.t);
			return res;
		};
		const buildSegmentsClipped = (pts: { x: number; y: number }[]) => {
			if (!rect) return pts.length > 1 ? [pts] : [];
			const out: { x: number; y: number }[][] = [];
			let seg: { x: number; y: number }[] = [];
			for (let i = 1; i < pts.length; i++) {
				const a = pts[i - 1];
				const b = pts[i];
				const inA = isInside(a);
				const inB = isInside(b);
				if (!inA && !inB) {
					const ints = segmentRectIntersections(a, b);
					if (seg.length === 0) seg.push(a);
					if (ints.length === 2) {
						// a..i1 (fuera)
						seg.push({ x: ints[0].x, y: ints[0].y });
						if (seg.length > 1) out.push(seg);
						// i2.. (continuar fuera)
						seg = [{ x: ints[1].x, y: ints[1].y }];
					} else {
						seg.push(b);
					}
				} else if (inA && !inB) {
					const ints = segmentRectIntersections(a, b);
					const first = ints.find((it) => it.t >= 0 && it.t <= 1);
					if (first) {
						seg = [{ x: first.x, y: first.y }, b];
					} else {
						seg = [b];
					}
				} else if (!inA && inB) {
					const ints = segmentRectIntersections(a, b);
					const last = ints.reverse().find((it) => it.t >= 0 && it.t <= 1);
					if (seg.length === 0) seg.push(a);
					if (last) seg.push({ x: last.x, y: last.y });
					if (seg.length > 1) out.push(seg);
					seg = [];
				} else {
					// ambos dentro: cerrar segmento si estaba abierto
					if (seg.length > 1) out.push(seg);
					seg = [];
				}
			}
			if (seg.length > 1) out.push(seg);
			return out;
		};
		routePastSegments = buildSegmentsClipped(pastPts);
		routeFutureSegments = buildSegmentsClipped(futurePts);
		// Actualizar ruta completa también
		routeAllPoints = trackPoints.map(toXY);
		console.log('updateSelectedTrackRoute:end', {
			pastPts: pastPts.length,
			futurePts: futurePts.length,
			pastSegs: routePastSegments.map((s) => s.length),
			futureSegs: routeFutureSegments.map((s) => s.length)
		});
	}

	// --- FUNCIONES DE BACKEND Y CARGA DE DATOS ---
	async function updateBackendData() {
		try {
			const res = await apiFetch(`/task/${data.id}/update-data`, {
				method: 'POST',
				headers: { 'X-CSRF-Token': '1' },
				body: JSON.stringify({ rutas: rutas, indeterminados: indeterminados })
			});
			if (!res.ok) {
				let detail = '';
				try {
					const txt = await res.text();
					detail = txt;
				} catch {}
				throw new Error(detail || 'No se pudo guardar los cambios en el servidor.');
			}
			return true;
		} catch (e: any) {
			// No cambiar a estado de error global para no ocultar la UI
			const message = e?.message || 'No se pudo guardar los cambios en el servidor.';
			showError(message);
			// Re-sincronizar estado con el backend para evitar inconsistencias
			try {
				if (data?.id) await fetchData(data.id);
			} catch {}
			return false;
		}
	}
	async function fetchData(taskId: string) {
		loading = true;
		error = null;
		generalReady = false;
		try {
			const res = await apiFetch(`/task/${taskId}`);
			if (!res.ok) throw new Error(`Error al obtener datos: ${res.statusText}`);
			const apiData = await res.json();

			// Meta del video
			videoPath = apiData.videoPath ?? '';
			videoWidth = +apiData.videoWidth;
			videoHeight = +apiData.videoHeight;
			videoFps = +apiData.videoFps;
			console.log('Video meta:', { videoPath, videoWidth, videoHeight, videoFps });

			// Helper para evitar caché del navegador en JSON estáticos de MinIO
			const bust = (url: string) => `${url}${url.includes('?') ? '&' : '?'}_ts=${Date.now()}`;

			// Obtener historial: inline o vía URLs públicas (MinIO)
			const historyPromise: Promise<any> = apiData.history
				? Promise.resolve(apiData.history)
				: apiData.historyUrl
					? fetch(bust(apiData.historyUrl))
							.then((r) => {
								if (!r.ok) throw new Error(`Error al obtener historial: ${r.statusText}`);
								return r.json();
							})
							.then((d) => d.history ?? d)
					: Promise.resolve({});

			// --- Procesar data_obj_history.json para bboxes y recorridos ---
			let generalHistoryUrl =
				apiData.dataObjHistoryUrl || apiData.data_obj_history_url || apiData.historyUrl;
			console.log('General history URL:', generalHistoryUrl);
			if (generalHistoryUrl) {
				const generalRes = await fetch(bust(generalHistoryUrl));
				if (!generalRes.ok) throw new Error('Error al obtener data_obj_history.json');
				const generalJson = await generalRes.json();
				console.log('General JSON keys:', Object.keys(generalJson));
				// Procesar a Map<frame, [bboxes]> y Map<trackId, TrackPoint[]>
				const frameMap = new Map<number, GeneralBBox[]>();
				const trackMap = new Map<string, TrackPoint[]>();
				let totalBBoxes = 0;
				for (const [trackId, arr] of Object.entries(generalJson as Record<string, any[]>)) {
					const points: TrackPoint[] = [];
					for (const obj of arr) {
						const frame = Number(obj.act_frame);
						if (!frameMap.has(frame)) frameMap.set(frame, []);
						frameMap.get(frame)!.push({ id: String(trackId), box: obj.box });
						points.push({ frame, box: obj.box });
						totalBBoxes++;
					}
					points.sort((a, b) => a.frame - b.frame);
					trackMap.set(String(trackId), points);
				}
				generalBBoxesByFrame = frameMap;
				generalTrackHistory = trackMap;
				// Calcular rango de frames para mapeo calibrado tiempo<->frame
				const frames = Array.from(frameMap.keys());
				if (frames.length) {
					dataFrameFirst = Math.min(...frames);
					dataFrameLast = Math.max(...frames);
					console.log('Frame range:', { dataFrameFirst, dataFrameLast, count: frames.length });
				} else {
					dataFrameFirst = null;
					dataFrameLast = null;
				}
				console.log('Tracks con historial:', generalTrackHistory.size);
				console.log('Total bboxes procesadas:', totalBBoxes);
				console.log('Frames con bboxes:', Array.from(frameMap.keys()));
				generalReady = true;
			} else {
				generalBBoxesByFrame = new Map();
				generalTrackHistory = new Map();
				dataFrameFirst = null;
				dataFrameLast = null;
				generalReady = true;
			}

			rutas = apiData.rutas;
			indeterminados = apiData.indeterminados;
			determinados = apiData.determinados || {};
			console.log('Datos de rutas cargados:', {
				determinados: Object.keys(determinados || {}).length,
				indeterminados: Object.keys(indeterminados || {}).length
			});
			history = await historyPromise;

			sortedIndeterminados = Object.entries(indeterminados).sort(([, a], [, b]) => {
				const aIsEntradaConocida = a.labels[0] !== 'IND' && a.labels[1] === 'IND';
				const bIsEntradaConocida = b.labels[0] !== 'IND' && b.labels[1] === 'IND';
				if (aIsEntradaConocida && !bIsEntradaConocida) return -1;
				if (!aIsEntradaConocida && bIsEntradaConocida) return 1;
				return parseInt(a.first_appearance.frame) - parseInt(b.first_appearance.frame);
			});
		} catch (e: any) {
			error = e.message || 'Error desconocido al cargar los datos.';
			generalReady = false;
		} finally {
			loading = false;
		}
	}
	onMount(() => {
		const taskId = data.id;
		if (taskId) fetchData(taskId);
		else {
			error = 'No se proporcionó un ID de tarea.';
			loading = false;
		}
		window.addEventListener('resize', updateVideoDimensions);
		return () => {
			window.removeEventListener('resize', updateVideoDimensions);
			stopAnimationLoop();
		};
	});
	function handleKeyPress(event: KeyboardEvent, trackId: string) {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			handleIndeterminateClick(trackId);
		}
	}
	async function handleConfirm(trackId: string, event: MouseEvent) {
		event.stopPropagation();
		const item = indeterminados[trackId];
		if (!item) return;
		savingById[trackId] = true;
		sortedIndeterminados = sortedIndeterminados.filter(([id]) => id !== trackId);
		if (activeBoundingBox === item.first_appearance.boundingBox) activeBoundingBox = null;
		playbackBoundingBoxes = playbackBoundingBoxes.filter((b) => b.id !== trackId);
		if (activeIndeterminateId === trackId) activeIndeterminateId = null;

		const [entrada, salida] = item.labels;
		const vehiculo = item.class;

		if (rutas[entrada]?.[salida]?.[vehiculo] !== undefined) {
			rutas[entrada][salida][vehiculo]++;
		} else {
			if (!rutas[entrada]) rutas[entrada] = {};
			if (!rutas[entrada][salida]) rutas[entrada][salida] = {};
			vehicleTypes.forEach((v) => {
				if (rutas[entrada][salida][v] === undefined) {
					rutas[entrada][salida][v] = 0;
				}
			});
			rutas[entrada][salida][vehiculo] = 1;
		}

		delete indeterminados[trackId];
		indeterminados = { ...indeterminados };
		rutas = { ...rutas };

		const ok = await updateBackendData();
		if (ok) {
			showSuccess(`Vehículo ${trackId} confirmado y añadido a la ruta ${entrada} -> ${salida}.`);
		}
		delete savingById[trackId];
	}
	async function handleDelete(trackId: string, event: MouseEvent) {
		event.stopPropagation();
		const item = indeterminados[trackId];
		savingById[trackId] = true;
		sortedIndeterminados = sortedIndeterminados.filter(([id]) => id !== trackId);
		if (item && activeBoundingBox === item.first_appearance.boundingBox) activeBoundingBox = null;
		playbackBoundingBoxes = playbackBoundingBoxes.filter((b) => b.id !== trackId);
		if (activeIndeterminateId === trackId) activeIndeterminateId = null;

		delete indeterminados[trackId];
		indeterminados = { ...indeterminados };

		const ok = await updateBackendData();
		if (ok) {
			showSuccess(`Vehículo indeterminado ${trackId} eliminado.`);
		}
		delete savingById[trackId];
	}
	let vehicleTypes = $derived.by(() => {
		if (Object.keys(rutas).length === 0) return [];
		const allTypes = new Set<string>();
		for (const entrada in rutas) {
			for (const salida in rutas[entrada]) {
				Object.keys(rutas[entrada][salida]).forEach((v) => allTypes.add(v));
			}
		}
		Object.values(indeterminados).forEach((item) => allTypes.add(item.class));
		return Array.from(allTypes).sort();
	});
	let zoneIds = $derived.by(() => {
		if (Object.keys(rutas).length === 0) return [];
		const allZones = new Set<string>();
		Object.keys(rutas).forEach((id) => allZones.add(id));
		Object.values(rutas).forEach((salidas) =>
			Object.keys(salidas).forEach((id) => allZones.add(id))
		);
		return Array.from(allZones).sort();
	});

	// Opciones para los selects personalizados (GlassSelect)
	let vehicleItems = $derived.by(() =>
		vehicleTypes.map((v) => ({ value: v, label: getVehicleName(v) }))
	);
	let zoneItems = $derived.by(() => [
		{ value: 'IND', label: 'IND' },
		...zoneIds.map((z) => ({ value: z, label: `Zona ${z}` }))
	]);
	let entradasData = $derived.by(() => {
		if (Object.keys(rutas).length === 0) return null;
		const entradasIds = Object.keys(rutas).sort();
		const columnasPrincipales = entradasIds.map((id) => `Entrada ${id}`);
		const totalGeneral: FilaTabla = {
			tipo: 'Total',
			...Object.fromEntries(columnasPrincipales.map((c) => [c, 0]))
		};
		const datos = vehicleTypes.map((vehiculo) => {
			const fila: FilaTabla = { tipo: getVehicleName(vehiculo) };
			entradasIds.forEach((entradaId) => {
				const nombreColumna = `Entrada ${entradaId}`;
				const totalVehiculoPorEntrada = Object.values(rutas[entradaId] || {}).reduce(
					(sum, salida) => sum + (salida[vehiculo] ?? 0),
					0
				);
				fila[nombreColumna] = totalVehiculoPorEntrada;
				(totalGeneral[nombreColumna] as number) += totalVehiculoPorEntrada;
			});
			return fila;
		});
		return {
			titulo: 'Resumen de Entradas por Zona',
			columnasPrincipales,
			datos,
			total: totalGeneral
		};
	});
	let salidasData = $derived.by(() => {
		if (Object.keys(rutas).length === 0) return null;
		const salidasIds = [...new Set(Object.values(rutas).flatMap(Object.keys))].sort();
		const columnasPrincipales = salidasIds.map((id) => `Salida ${id}`);
		const totalGeneral: FilaTabla = {
			tipo: 'Total',
			...Object.fromEntries(columnasPrincipales.map((c) => [c, 0]))
		};
		const datos = vehicleTypes.map((vehiculo) => {
			const fila: FilaTabla = { tipo: getVehicleName(vehiculo) };
			salidasIds.forEach((salidaId) => {
				const nombreColumna = `Salida ${salidaId}`;
				let totalVehiculoPorSalida = 0;
				for (const entradaId in rutas) {
					totalVehiculoPorSalida += rutas[entradaId]?.[salidaId]?.[vehiculo] ?? 0;
				}
				fila[nombreColumna] = totalVehiculoPorSalida;
				(totalGeneral[nombreColumna] as number) += totalVehiculoPorSalida;
			});
			return fila;
		});
		return {
			titulo: 'Resumen de Salidas por Zona',
			columnasPrincipales,
			datos,
			total: totalGeneral
		};
	});
	let rutasData = $derived.by(() => {
		if (Object.keys(rutas).length === 0) return null;
		const entradasIds = Object.keys(rutas).sort();
		const entradasDetalle = entradasIds.map((entradaId) => {
			const salidasDeEntradaIds = Object.keys(rutas[entradaId]).sort();
			const columnasSalida = salidasDeEntradaIds.map((id) => `Salida ${id}`);
			const totalEntrada: FilaTabla = {
				tipo: 'Total',
				...Object.fromEntries(columnasSalida.map((c) => [c, 0]))
			};
			const datos = vehicleTypes.map((vehiculo) => {
				const fila: FilaTabla = { tipo: getVehicleName(vehiculo) };
				salidasDeEntradaIds.forEach((salidaId) => {
					const nombreColumna = `Salida ${salidaId}`;
					const conteo = rutas[entradaId][salidaId][vehiculo] ?? 0;
					fila[nombreColumna] = conteo;
					(totalEntrada[nombreColumna] as number) += conteo;
				});
				return fila;
			});
			return {
				nombreEntrada: `Desde Entrada ${entradaId}`,
				columnasSalida,
				datos,
				total: totalEntrada
			};
		});
		return { titulo: 'Detalle de Rutas (Entrada -> Salida)', entradasDetalle };
	});
	function downloadVideo() {
		if (!data?.id) return;
		const url = `/api/task/${data.id}/download`;
		fetch(url, { credentials: 'include' })
			.then(async (res) => {
				if (!res.ok) throw new Error('No se pudo descargar el video');
				const blob = await res.blob();
				const contentDisp = res.headers.get('Content-Disposition');
				let filename = 'video.mp4';
				if (contentDisp) {
					const match = /filename="?([^";]+)"?/i.exec(contentDisp);
					if (match?.[1]) filename = match[1];
				}
				const link = document.createElement('a');
				link.href = URL.createObjectURL(blob);
				link.download = filename;
				link.click();
				URL.revokeObjectURL(link.href);
				showSuccess('Descarga iniciada');
			})
			.catch((e) => showError(e.message || 'Error al iniciar la descarga'));
	}

	// Helper para mostrar nombres de vehículos en UI
	function getVehicleName(key: string): string {
		if (!key) return 'N/A';
		return key.charAt(0).toUpperCase() + key.slice(1).toLowerCase().replaceAll(/_/g, ' ');
	}
</script>

<div class="min-h-screen bg-background text-foreground py-8 px-4">
	<h1 class="text-3xl font-bold mb-4 text-center">Revisar Video Analizado</h1>

	{#if loading}
		<p class="text-center text-xl">Cargando datos de la tarea...</p>
	{:else if error}
		<div
			class="bg-red-900 border border-red-600 text-red-100 px-4 py-3 rounded-lg text-center"
			role="alert"
		>
			<strong class="font-bold">¡Error!</strong>
			<span class="block sm:inline">{error}</span>
		</div>
	{:else}
		<div class="flex flex-wrap justify-center items-start gap-8 mb-12">
			<!-- Reproductor de video -->
			<div class="w-full lg:w-2/3 max-w-5xl">
				{#if videoPath !== '' && generalReady}
					<div
						class="relative rounded overflow-hidden border bg-black aspect-video glass-card"
						style="border-color: hsl(var(--border))"
					>
						<video
							class="w-full h-full"
							controls
							autoplay
							loop
							bind:this={videoElement}
							onloadedmetadata={() => {
								videoDuration = videoElement?.duration ?? 0;
								updateVideoDimensions();
								if (selectedTrackId && videoElement) {
									updateSelectedTrackRoute(computeCurrentFrameFromTime(videoElement.currentTime));
								}
							}}
							onplay={startAnimationLoop}
							onpause={stopAnimationLoop}
							onseeking={() => {
								if (videoElement) {
									lastProcessedFrame = computeCurrentFrameFromTime(videoElement.currentTime) - 1;
								}
							}}
						>
							<source src={videoPath} type="video/mp4" />
							<track kind="captions" />
							Tu navegador no soporta la reproducción de video.
						</video>

						<!-- Renderizado de bboxes generales (sin fade, sin ID) -->
						{#each generalDisplayBBoxes as box (box.id)}
							<div
								class="general-bbox"
								role="button"
								tabindex="0"
								aria-label="Mostrar ruta del vehículo"
								style={calculateGeneralBoxStyle(box)}
								onclick={() => showRouteFor(box)}
								onkeydown={(e) => {
									if (e.key === 'Enter' || e.key === ' ') {
										e.preventDefault();
										showRouteFor(box);
									}
								}}
							></div>
						{/each}

						<!-- Overlay de recorrido de track seleccionado (contenedor único) -->
						{#if selectedTrackId}
							{#key routeAnimateKey}
								<svg
									class="absolute inset-0 pointer-events-none"
									style="z-index: 13;"
									width="100%"
									height="100%"
								>
									<defs>
										<filter id="white-glow" x="-50%" y="-50%" width="200%" height="200%">
											<feGaussianBlur stdDeviation="2.5" result="coloredBlur" />
											<feMerge>
												<feMergeNode in="coloredBlur" />
												<feMergeNode in="SourceGraphic" />
											</feMerge>
										</filter>
										{#if selectedBoxRect}
											<mask id="mask-outside-bbox">
												<!-- Blanco = visible; Negro = oculto dentro del bbox -->
												<rect x="0" y="0" width="100%" height="100%" fill="white" />
												<rect
													x={selectedBoxRect.x}
													y={selectedBoxRect.y}
													width={selectedBoxRect.width}
													height={selectedBoxRect.height}
													fill="black"
												/>
											</mask>
										{/if}
									</defs>
									{#each routePastSegments as seg, i}
										{#if seg.length > 1}
											<polyline
												points={[...seg]
													.reverse()
													.map((p) => `${p.x},${p.y}`)
													.join(' ')}
												fill="none"
												stroke="#ffffff"
												stroke-width="2.5"
												stroke-linecap="round"
												stroke-linejoin="round"
												filter="url(#white-glow)"
												pathLength="1"
												class={routeAnimating ? 'route-anim' : ''}
												style={routeAnimating ? `animation-delay: ${i * 35}ms;` : undefined}
											/>
										{/if}
									{/each}
									{#each routeFutureSegments as seg, i}
										{#if seg.length > 1}
											<polyline
												points={seg.map((p) => `${p.x},${p.y}`).join(' ')}
												fill="none"
												stroke="#ffffff"
												stroke-width="2"
												stroke-linecap="round"
												stroke-linejoin="round"
												opacity="0.5"
												pathLength="1"
												class={routeAnimating ? 'route-anim' : ''}
												style={routeAnimating ? `animation-delay: ${i * 35}ms;` : undefined}
											/>
										{/if}
									{/each}
								</svg>
							{/key}
						{/if}

						<!-- Renderizado de bboxes indeterminados (con fade, con ID) -->
						{#each displayBoundingBoxes as box (box.id)}
							<div class="bbox-style" style={calculateBoxStyle(box)}>
								{#if box.id !== 'active-manual'}
									<div class="bbox-id-label">ID: {box.id}</div>
								{/if}
							</div>
						{/each}
					</div>
				{:else}
					<div
						class="flex items-center justify-center w-full h-full min-h-[320px]"
						style="background: #111;"
					>
						<Spinner size={48} />
					</div>
				{/if}
			</div>

			<!-- Lista de indeterminados -->
			{#if sortedIndeterminados.length > 0}
				<div
					class="w-full md:w-auto glass-card p-1 rounded-lg shadow-lg max-w-[450px] overflow-y-auto"
					style:height={videoHeightPx > 0 ? `${videoHeightPx}px` : 'auto'}
				>
					<h3 class="text-xl font-semibold mt-3 mb-3 text-center">Vehículos Indeterminados</h3>

					<div class="overflow-y-auto flex-1">
						<div class="space-y-3 p-1">
							{#each sortedIndeterminados as [trackId, item] (trackId)}
								{@const [entrada, salida] = item.labels}
								{@const canConfirm = entrada !== 'IND' && salida !== 'IND'}
								<div
									class="ind-card"
									class:live={liveIndeterminateIds.has(trackId) ||
										trackId === activeIndeterminateId}
									role="button"
									tabindex="0"
									onclick={() => handleIndeterminateClick(trackId)}
									onkeydown={(e) => handleKeyPress(e, trackId)}
								>
									<div class="flex justify-between items-center mb-2">
										<p class="font-bold text-lg">ID: {trackId}</p>
										<button
											onclick={(e) => handleDelete(trackId, e)}
											class="glass-button btn-danger text-xs py-1 px-2 disabled:opacity-60 disabled:cursor-not-allowed"
											disabled={savingById[trackId]}
										>
											{#if savingById[trackId]}
												<Spinner size={14} className="inline-block mr-1" />
												Eliminando...
											{:else}
												Eliminar
											{/if}
										</button>
									</div>
									<div class="grid grid-cols-3 gap-2 items-center mb-2 text-sm">
										<span class="text-gray-400">Clase:</span>
										<div class="col-span-2">
											<GlassSelect
												items={vehicleItems}
												value={indeterminados[trackId].class}
												ariaLabel={`Clase para ${trackId}`}
												stopClickPropagation={true}
												onChange={(val) => (indeterminados[trackId].class = String(val ?? ''))}
											/>
										</div>
									</div>
									<div class="grid grid-cols-3 gap-2 items-center mb-3 text-sm">
										<span class="text-gray-400">Ruta:</span>
										<div class="col-span-2 flex items-center gap-1">
											<div class="w-full">
												<GlassSelect
													items={zoneItems}
													value={indeterminados[trackId].labels[0]}
													ariaLabel={`Entrada para ${trackId}`}
													stopClickPropagation={true}
													onChange={(val) =>
														(indeterminados[trackId].labels[0] = String(val ?? 'IND'))}
												/>
											</div>
											<span class="text-gray-400">→</span>
											<div class="w-full">
												<GlassSelect
													items={zoneItems}
													value={indeterminados[trackId].labels[1]}
													ariaLabel={`Salida para ${trackId}`}
													stopClickPropagation={true}
													onChange={(val) =>
														(indeterminados[trackId].labels[1] = String(val ?? 'IND'))}
												/>
											</div>
										</div>
									</div>
									<button
										onclick={(e) => handleConfirm(trackId, e)}
										disabled={!canConfirm || savingById[trackId]}
										class="w-full py-2 text-sm font-semibold rounded flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed glass-button"
										class:btn-success={canConfirm}
									>
										{#if savingById[trackId]}
											<Spinner size={16} />
											Guardando...
										{:else}
											Confirmar Ruta
										{/if}
									</button>
								</div>
							{/each}
						</div>
					</div>
				</div>
			{/if}
		</div>

		<!-- Sección de Estadísticas -->
		<div class="max-w-7xl mx-auto space-y-12">
			<!-- Tablas de Resumen (Entradas y Salidas) -->
			<div class="grid grid-cols-1 md:grid-cols-2 gap-8">
				<!-- Tabla de Entradas -->
				{#if entradasData}
					<div class="glass-card p-6 rounded-lg shadow-lg">
						<h2 class="text-2xl font-semibold mb-4 text-center">{entradasData.titulo}</h2>
						<div class="overflow-x-auto">
							<table class="w-full text-sm text-left">
								<thead class="text-xs uppercase glass-surface">
									<tr>
										<th scope="col" class="px-4 py-3">Vehículo</th>
										{#each entradasData.columnasPrincipales as col}
											<th scope="col" class="px-4 py-3 text-center">{col}</th>
										{/each}
									</tr>
								</thead>
								<tbody>
									{#each entradasData.datos as item}
										<tr
											class="border-b hover:glass-surface"
											style="border-color: hsl(var(--border))"
										>
											<td class="px-4 py-2 font-medium whitespace-nowrap">{item.tipo}</td>
											{#each entradasData.columnasPrincipales as col}
												<td class="px-4 py-2 text-center">{item[col]}</td>
											{/each}
										</tr>
									{/each}
									<tr class="font-semibold glass-surface">
										<td class="px-4 py-2">{entradasData.total.tipo}</td>
										{#each entradasData.columnasPrincipales as col}
											<td class="px-4 py-2 text-center">{entradasData.total[col]}</td>
										{/each}
									</tr>
								</tbody>
							</table>
						</div>
					</div>
				{/if}

				<!-- Tabla de Salidas -->
				{#if salidasData}
					<div class="glass-card p-6 rounded-lg shadow-lg">
						<h2 class="text-2xl font-semibold mb-4 text-center">{salidasData.titulo}</h2>
						<div class="overflow-x-auto">
							<table class="w-full text-sm text-left">
								<thead class="text-xs uppercase glass-surface">
									<tr>
										<th scope="col" class="px-4 py-3">Vehículo</th>
										{#each salidasData.columnasPrincipales as col}
											<th scope="col" class="px-4 py-3 text-center">{col}</th>
										{/each}
									</tr>
								</thead>
								<tbody>
									{#each salidasData.datos as item}
										<tr
											class="border-b hover:glass-surface"
											style="border-color: hsl(var(--border))"
										>
											<td class="px-4 py-2 font-medium whitespace-nowrap">{item.tipo}</td>
											{#each salidasData.columnasPrincipales as col}
												<td class="px-4 py-2 text-center">{item[col]}</td>
											{/each}
										</tr>
									{/each}
									<tr class="font-semibold glass-surface">
										<td class="px-4 py-2">{salidasData.total.tipo}</td>
										{#each salidasData.columnasPrincipales as col}
											<td class="px-4 py-2 text-center">{salidasData.total[col]}</td>
										{/each}
									</tr>
								</tbody>
							</table>
						</div>
					</div>
				{/if}
			</div>

			<!-- Tabla detallada de Rutas -->
			{#if rutasData}
				<div class="glass-card p-6 rounded-lg shadow-lg">
					<h2 class="text-2xl font-semibold mb-6 text-center">{rutasData.titulo}</h2>
					<div class="space-y-8">
						{#each rutasData.entradasDetalle as entrada}
							<div>
								<h3 class="text-xl font-medium mb-3 opacity-80">{entrada.nombreEntrada}</h3>
								<div class="overflow-x-auto">
									<table class="w-full text-sm text-left">
										<thead class="text-xs uppercase glass-surface">
											<tr>
												<th scope="col" class="px-4 py-3">Vehículo</th>
												{#each entrada.columnasSalida as colName}
													<th scope="col" class="px-4 py-3 text-center">{colName}</th>
												{/each}
											</tr>
										</thead>
										<tbody>
											{#each entrada.datos as item}
												<tr
													class="border-b hover:glass-surface"
													style="border-color: hsl(var(--border))"
												>
													<td class="px-4 py-2 font-medium whitespace-nowrap">{item.tipo}</td>
													{#each entrada.columnasSalida as colName}
														<td class="px-4 py-2 text-center">{item[colName]}</td>
													{/each}
												</tr>
											{/each}
											<tr class="font-semibold glass-surface">
												<td class="px-4 py-2">{entrada.total.tipo}</td>
												{#each entrada.columnasSalida as colName}
													<td class="px-4 py-2 text-center">{entrada.total[colName]}</td>
												{/each}
											</tr>
										</tbody>
									</table>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.overflow-y-auto::-webkit-scrollbar {
		width: 8px;
	}
	.overflow-y-auto::-webkit-scrollbar-track {
		background: #2a2f3a;
		border-radius: 10px;
	}
	.overflow-y-auto::-webkit-scrollbar-thumb {
		background-color: #4a5568;
		border-radius: 10px;
		border: 2px solid #2a2f3a;
	}
	.overflow-y-auto::-webkit-scrollbar-thumb:hover {
		background-color: #718096;
	}
	.bbox-style {
		/* Borde blanco, 2px es un buen punto de partida */
		border: 2px solid #ffffff;

		/* Múltiples box-shadow para un efecto de neón más intenso.
		   Se apilan de atrás hacia adelante. */
		box-shadow:
			0 0 5px rgba(255, 255, 255, 0.8),
			/* Resplandor interior cercano */ 0 0 10px rgba(255, 255, 255, 0.6),
			/* Resplandor medio */ 0 0 20px rgba(255, 255, 255, 0.4); /* Resplandor exterior más difuso */

		pointer-events: none;
		z-index: 10;
		transition: transform 0.2s ease-in-out;
	}
	.general-bbox {
		/* Rectángulo completo, borde blanco, sin glow */
		border: 2px solid #ffffff;
		box-shadow: none;
		pointer-events: auto;
		z-index: 12;
		position: absolute;
		cursor: pointer;
	}
	.ind-card {
		/* Preserve glow behavior, but retheme base surface into glass */
		background-color: hsl(var(--background) / 0.6);
		padding: 0.75rem;
		border-radius: 12px;
		border: 1px solid hsl(var(--border));
		cursor: pointer;
		transition:
			border-color 0.2s ease-in-out,
			box-shadow 0.2s ease-in-out,
			background-color 0.2s ease-in-out,
			color 0.2s ease-in-out;
		outline: none;
		backdrop-filter: blur(10px);
		-webkit-backdrop-filter: blur(10px);
	}

	/* 1. Resplandor débil para hover (sin cambios) */
	.ind-card:hover {
		border-color: rgba(255, 255, 255, 0.35);
		box-shadow: 0 0 8px rgba(255, 255, 255, 0.2);
	}

	/* 2. Resplandor fuerte para la tarjeta "en vivo" durante la reproducción */
	.ind-card.live {
		transition: none;
		border-color: #ffffff;
		box-shadow:
			0 0 3px rgba(255, 255, 255, 0.5),
			0 0 7px rgba(255, 255, 255, 0.7);
	}

	/* --- ESTILO AÑADIDO PARA LA ETIQUETA DEL ID DE LA BBOX --- */
	.bbox-id-label {
		/* Posicionamiento: arriba y a la izquierda de la BBox */
		position: absolute;
		bottom: 100%;
		left: -2px; /* Alineado con el borde de la BBox */
		margin-bottom: 5px; /* Pequeño espacio sobre la BBox */

		/* Estilo del contenedor para máxima legibilidad */
		background-color: rgba(0, 0, 0, 0.75); /* Fondo negro semitransparente */
		padding: 2px 8px;
		border-radius: 4px;

		/* Estilo del texto */
		color: white;
		font-family:
			system-ui,
			-apple-system,
			BlinkMacSystemFont,
			'Segoe UI',
			Roboto,
			Oxygen,
			Ubuntu,
			Cantarell,
			'Open Sans',
			'Helvetica Neue',
			sans-serif;
		font-size: 12px;
		font-weight: 600;
		white-space: nowrap; /* Evita que el ID se parta en dos líneas */

		/* Un suave resplandor al texto para que se integre mejor */
		text-shadow: 0 0 5px rgba(0, 0, 0, 0.9);
	}

	/* Animación de trazo para dibujar la ruta rápidamente (sutil) */
	@keyframes draw-in {
		from {
			stroke-dashoffset: 1;
		}
		to {
			stroke-dashoffset: 0;
		}
	}

	.route-anim {
		stroke-dasharray: 1;
		stroke-dashoffset: 1;
		animation: draw-in 220ms ease-out forwards;
	}
</style>

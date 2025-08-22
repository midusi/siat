<script lang="ts">
	import { onMount } from 'svelte';
	import { apiFetch } from '$lib/api';
	import { showSuccess, showError } from '$lib/toast';
	import Spinner from '$lib/components/Spinner.svelte';
	import GlassSelect from '$lib/components/GlassSelect.svelte';
	import { showConfirm } from '$lib/dialog';

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
	// Fade out de ruta/selección cuando desaparece del frame
	let routeFadingOut = $state(false);
	let routeFadeTimer: any = null;
	// Controla si la selección aplica atenuación al resto (permite restaurar opacidad mientras la ruta se desvanece)
	let isSelectionActive = $state(false);
	// Rect del bbox seleccionado en el frame actual (para ocultar ruta dentro del bbox)
	let selectedBoxRect = $state<{ x: number; y: number; width: number; height: number } | null>(
		null
	);

	// Nota: 'selectedRoute' no se usa en la UI; se elimina para evitar trabajo inútil

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
	// --- Búsqueda de indeterminados por ID ---
	let searchQuery = $state('');
	let searchInputEl = $state<HTMLInputElement | null>(null);
	let visibleIndeterminados = $derived.by(() => {
		const q = (searchQuery || '').trim();
		if (!q) return sortedIndeterminados;
		return sortedIndeterminados.filter(([id]) => id.includes(q));
	});
	let videoScale = $state({ x: 1, y: 1 });
	let savingById = $state<Record<string, boolean>>({});
	let history = $state<History>({});
	// Rango de frames disponibles (para mapear tiempo->frame sin depender estrictamente de FPS)
	let dataFrameFirst = $state<number | null>(null);
	let dataFrameLast = $state<number | null>(null);

	// --- Estado Modo Unir ---
	let mergeModeActive = $state(false);
	let mergeSourceId = $state<string | null>(null);
	let mergeInProgress = $state(false);

	function isUnknownLabel(x: string | null | undefined): boolean {
		return !x || x === 'IND';
	}

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

	function isFrameWithinTrackRange(trackId: string, frame: number): boolean {
		const points = generalTrackHistory.get(trackId) || [];
		if (!points.length) return false;
		const first = points[0].frame;
		const last = points[points.length - 1].frame;
		return frame >= first && frame <= last;
	}

	// --- Utilidades de geometría y estilos (para evitar duplicación) ---
	type Rect = { x: number; y: number; width: number; height: number };
	function toScaledClampedRect(box: [number, number, number, number]): Rect | null {
		if (!videoElement) return null;
		const [x1n, y1n, x2n, y2n] = box;
		const vw = videoElement.clientWidth,
			vh = videoElement.clientHeight;
		let left = x1n * videoScale.x;
		let top = y1n * videoScale.y;
		let width = (x2n - x1n) * videoScale.x;
		let height = (y2n - y1n) * videoScale.y;
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
		if (left + width > vw) width = vw - left;
		if (top + height > vh) height = vh - top;
		if (width <= 0 || height <= 0) return null;
		return { x: left, y: top, width, height };
	}
	function toScaledClampedRectFromStr(bbox: BoundingBox): Rect | null {
		const [x1s, y1s, x2s, y2s] = bbox;
		return toScaledClampedRect([
			parseFloat(x1s),
			parseFloat(y1s),
			parseFloat(x2s),
			parseFloat(y2s)
		]);
	}
	function rectStyle(rect: Rect, extra = ''): string {
		return `position: absolute; left: ${rect.x}px; top: ${rect.y}px; width: ${rect.width}px; height: ${rect.height}px; ${extra}`;
	}
	function boxCenterScaled(box: [number, number, number, number]) {
		const [x1, y1, x2, y2] = box;
		return { x: ((x1 + x2) / 2) * videoScale.x, y: ((y1 + y2) / 2) * videoScale.y };
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
		// Actualizar rect del bbox seleccionado (si está en el frame actual)
		if (selectedTrackId && videoElement) {
			const sel = generalDisplayBBoxes.find((b) => b.id === selectedTrackId);
			selectedBoxRect = sel ? toScaledClampedRect(sel.box) : selectedBoxRect; // conservar para evitar parpadeos
		} else {
			selectedBoxRect = null;
		}
		// Ahora que tenemos el rect actualizado, calcular rutas/segmentos
		if (selectedTrackId) updateSelectedTrackRoute(currentFrame);
		// Decidir visibilidad según rango de frames del track
		if (selectedTrackId) {
			const inRange = isFrameWithinTrackRange(selectedTrackId, currentFrame);
			if (!inRange) beginClearSelectionWithFade();
		}

		// --- Indeterminados (con desvanecimiento, como antes) ---
		if (playbackBoundingBoxes.length > 0) {
			const out: DisplayableBBox[] = [];
			for (const box of playbackBoundingBoxes) {
				const timeUntilHidden = box.hideAtTime - currentTime;
				const newOpacity = Math.max(0, Math.min(1.0, timeUntilHidden / FADE_OUT_DURATION_SECONDS));
				if (newOpacity > 0) {
					if (newOpacity !== box.opacity) out.push({ ...box, opacity: newOpacity });
					else out.push(box);
				}
			}
			playbackBoundingBoxes = out; // reasignación para reactividad
		}

		// Añadir nuevas bboxes indeterminadas si hemos avanzado a un nuevo frame
		if (currentFrame > lastProcessedFrame) {
			let updated = playbackBoundingBoxes.slice();
			for (let frame = lastProcessedFrame + 1; frame <= currentFrame; frame++) {
				const bboxesInfo = indeterminadosByFrame.get(frame);
				if (bboxesInfo) {
					for (const info of bboxesInfo) {
						updated.push({
							id: info.trackId,
							bbox: info.bbox,
							hideAtTime: computeTimeFromFrame(frame) + FADE_OUT_DURATION_SECONDS,
							opacity: 1.0
						});
						// Al aparecer por primera vez en reproducción, resaltar y mostrar su tarjeta en la lista
						activeIndeterminateId = info.trackId;
						queueMicrotask(() => {
							const el = document.getElementById(`ind-card-${info.trackId}`);
							if (el) {
								el.scrollIntoView({ behavior: 'smooth', block: 'center' });
								(el as HTMLElement).focus({ preventScroll: true });
							}
						});
					}
				}
			}
			playbackBoundingBoxes = updated;
		}

		lastProcessedFrame = currentFrame;
		lastVideoTime = currentTime;
		animationFrameId = requestAnimationFrame(animationLoop);
	}

	// Actualiza overlays (bboxes generales y ruta seleccionada) para el frame actual cuando el video está pausado
	function updateOverlaysForCurrentFrame() {
		if (!videoElement) return;
		const currentTime = videoElement.currentTime;
		const currentFrame = computeCurrentFrameFromTime(currentTime);
		// BBoxes generales del frame actual
		generalDisplayBBoxes = generalBBoxesByFrame.get(currentFrame) ?? [];
		// Rect del bbox seleccionado si existe en este frame
		if (selectedTrackId) {
			const sel = generalDisplayBBoxes.find((b) => b.id === selectedTrackId);
			selectedBoxRect = sel ? toScaledClampedRect(sel.box) : selectedBoxRect; // conservar si falta el bbox puntual
		} else {
			selectedBoxRect = null;
		}
		// Recalcular rutas para el frame actual
		if (selectedTrackId) updateSelectedTrackRoute(currentFrame);
		// Decidir visibilidad según rango de frames del track seleccionado
		if (selectedTrackId) {
			const inRange = isFrameWithinTrackRange(selectedTrackId, currentFrame);
			if (!inRange) beginClearSelectionWithFade();
		}
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

	// Recalcula escala y alto del contenedor en función del tamaño del video renderizado
	function updateVideoDimensions() {
		if (!videoElement) return;
		const vw = videoElement.videoWidth || videoWidth || 0;
		const vh = videoElement.videoHeight || videoHeight || 0;
		const cw = videoElement.clientWidth || 0;
		const ch = videoElement.clientHeight || 0;
		if (vw > 0 && vh > 0 && cw > 0 && ch > 0) {
			videoScale = { x: cw / vw, y: ch / vh };
			videoHeightPx = ch;
			// Si está pausado, actualizar overlays con la nueva escala
			if (videoElement.paused) updateOverlaysForCurrentFrame();
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

		// Apply the same selection behavior as clicking a bbox on video
		selectedTrackId = trackId;
		isSelectionActive = true;
		// Cancel any ongoing route fade
		if (routeFadeTimer) clearTimeout(routeFadeTimer);
		routeFadingOut = false;
		// Clear any separate indeterminate overlay to avoid double borders
		activeBoundingBox = null;
		// Fire quick route draw-in animation (reiniciar siempre)
		if (routeAnimTimer) clearTimeout(routeAnimTimer);
		routeAnimating = true;
		routeAnimTimer = setTimeout(() => (routeAnimating = false), 320);
		routeAnimateKey++;

		// Refresh overlays for the paused frame (sets selectedBoxRect and routes)
		updateOverlaysForCurrentFrame();
	}
	// CAMBIO 5: La función ahora recibe el objeto `DisplayableBBox` completo.
	function calculateBoxStyle(box: DisplayableBBox): string {
		if (!videoElement) return 'display: none;';
		const rect = toScaledClampedRectFromStr(box.bbox);
		if (!rect) return 'display: none;';
		return rectStyle(rect, `opacity: ${box.opacity}; transition: opacity 0.5s ease;`);
	}
	// --- BBoxes generales a mostrar (sin fade, sin ID) ---
	function calculateGeneralBoxStyle(box: GeneralBBox): string {
		if (!videoElement) return 'display: none;';
		const rect = toScaledClampedRect(box.box);
		if (!rect) return 'display: none;';
		const isSelected = selectedTrackId === box.id;
		const glow = isSelected
			? 'box-shadow: 0 0 5px rgba(255,255,255,0.8), 0 0 10px rgba(255,255,255,0.6), 0 0 20px rgba(255,255,255,0.4);'
			: 'box-shadow: none;';
		const dim = isSelectionActive && selectedTrackId && !isSelected ? 'opacity: 0.5;' : '';
		const borderColor = isSelected ? '#ffffff' : '#000000';
		return rectStyle(
			rect,
			`border: 2px solid ${borderColor}; ${glow} ${dim} pointer-events: auto; z-index: 12; cursor: pointer; transition: opacity 0.5s ease, box-shadow 0.5s ease;`
		);
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
		// Si ya está seleccionado y activo, hacer toggle para des-destacar con transición
		if (selectedTrackId === box.id) {
			if (isSelectionActive) {
				beginClearSelectionWithFade();
			}
			return;
		}
		selectedTrackId = box.id;
		isSelectionActive = true;
		// Cancelar cualquier fade-out en curso
		if (routeFadeTimer) clearTimeout(routeFadeTimer);
		routeFadingOut = false;
		const currentFrame = videoElement ? computeCurrentFrameFromTime(videoElement.currentTime) : 0;
		// Calcular de inmediato el rectángulo del bbox seleccionado (incluso si el video está en pausa)
		selectedBoxRect = toScaledClampedRect(box.box);
		const points = generalTrackHistory.get(box.id) || [];
		// Calcular la ruta completa con todos los puntos del track
		routeAllPoints = points.map((p) => boxCenterScaled(p.box));
		updateSelectedTrackRoute(currentFrame);
		// Disparar animación rápida (activar antes del remount para que las polylines nazcan animadas)
		if (routeAnimTimer) clearTimeout(routeAnimTimer);
		routeAnimating = true;
		routeAnimTimer = setTimeout(() => (routeAnimating = false), 320);
		// Incrementar clave para re-montar SVG y disparar animación
		routeAnimateKey++;

		// Si este track está en la lista de indeterminados, desplazarse a su tarjeta y resaltarla
		if (indeterminados[selectedTrackId]) {
			activeIndeterminateId = selectedTrackId;
			queueMicrotask(() => {
				const el = document.getElementById(`ind-card-${selectedTrackId}`);
				if (el) {
					el.scrollIntoView({ behavior: 'smooth', block: 'center' });
					(el as HTMLElement).focus({ preventScroll: true });
				}
			});
		}
	}

	function beginClearSelectionWithFade() {
		// Si ya no hay nada que mostrar, asegura estado limpio
		if (!selectedTrackId && routePastSegments.length === 0 && routeFutureSegments.length === 0) {
			routeFadingOut = false;
			isSelectionActive = false;
			return;
		}
		// Iniciar restauración visual inmediata del resto (quita atenuación)
		isSelectionActive = false;
		// Iniciar fade-out de la ruta overlay
		if (routeFadeTimer) clearTimeout(routeFadeTimer);
		routeFadingOut = true;
		routeFadeTimer = setTimeout(() => {
			routeFadingOut = false;
			selectedTrackId = null;
			selectedBoxRect = null;
			routePastPoints = [];
			routeFuturePoints = [];
			routeAllPoints = [];
			routePastSegments = [];
			routeFutureSegments = [];
		}, 500);
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
		const past = trackPoints.filter((p) => p.frame <= currentFrame);
		const future = trackPoints.filter((p) => p.frame > currentFrame);
		const toXY = (p: TrackPoint) => boxCenterScaled(p.box);
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
	}

	// --- FUNCIONES DE BACKEND Y CARGA DE DATOS ---
	function serializeDataObjHistory(): Record<
		string,
		{ act_frame: number; box: [number, number, number, number] }[]
	> {
		const out: Record<string, { act_frame: number; box: [number, number, number, number] }[]> = {};
		for (const [trackId, points] of generalTrackHistory.entries()) {
			out[trackId] = points
				.slice()
				.sort((a, b) => a.frame - b.frame)
				.map((p) => ({ act_frame: p.frame, box: p.box }));
		}
		return out;
	}
	async function updateBackendData() {
		try {
			const res = await apiFetch(`/task/${data.id}/update-data`, {
				method: 'POST',
				headers: { 'X-CSRF-Token': '1' },
				body: JSON.stringify({
					rutas: rutas,
					indeterminados: indeterminados,
					determinados,
					data_obj_history: serializeDataObjHistory()
				})
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
			// meta del video cargada

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
			if (generalHistoryUrl) {
				const generalRes = await fetch(bust(generalHistoryUrl));
				if (!generalRes.ok) throw new Error('Error al obtener data_obj_history.json');
				const generalJson = await generalRes.json();
				// Procesar a Map<frame, [bboxes]> y Map<trackId, TrackPoint[]>
				const frameMap = new Map<number, GeneralBBox[]>();
				const trackMap = new Map<string, TrackPoint[]>();
				for (const [trackId, arr] of Object.entries(generalJson as Record<string, any[]>)) {
					const points: TrackPoint[] = [];
					for (const obj of arr) {
						const frame = Number(obj.act_frame);
						if (!frameMap.has(frame)) frameMap.set(frame, []);
						frameMap.get(frame)!.push({ id: String(trackId), box: obj.box });
						points.push({ frame, box: obj.box });
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
				} else {
					dataFrameFirst = null;
					dataFrameLast = null;
				}
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
			history = await historyPromise;

			sortedIndeterminados = Object.entries(indeterminados).sort(([, a], [, b]) => {
				const aEntradaUnknown = !a.labels[0] || a.labels[0] === 'IND';
				const aSalidaUnknown = !a.labels[1] || a.labels[1] === 'IND';
				const bEntradaUnknown = !b.labels[0] || b.labels[0] === 'IND';
				const bSalidaUnknown = !b.labels[1] || b.labels[1] === 'IND';
				const aIsEntradaConocida = !aEntradaUnknown && aSalidaUnknown;
				const bIsEntradaConocida = !bEntradaUnknown && bSalidaUnknown;
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
		// Atajo global Ctrl+K para enfocar la barra de búsqueda y limpiar texto
		const onGlobalKeyDown = (e: KeyboardEvent) => {
			if (e.ctrlKey && (e.key === 'k' || e.key === 'K')) {
				e.preventDefault();
				searchQuery = '';
				queueMicrotask(() => searchInputEl?.focus());
			}
		};
		window.addEventListener('keydown', onGlobalKeyDown);
		return () => {
			window.removeEventListener('resize', updateVideoDimensions);
			window.removeEventListener('keydown', onGlobalKeyDown);
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
		savingById = { ...savingById };
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

		// Mover a determinados
		determinados[trackId] = {
			...item,
			// Normalizar: asegurar que first/last estén presentes y labels reflejen la ruta final
			first_appearance: item.first_appearance,
			last_appearance: item.last_appearance,
			labels: [entrada, salida]
		};
		// Eliminar de indeterminados
		delete indeterminados[trackId];
		indeterminados = { ...indeterminados };
		determinados = { ...determinados };
		rutas = { ...rutas };

		const ok = await updateBackendData();
		if (ok) {
			showSuccess(`Vehículo ${trackId} confirmado y añadido a la ruta ${entrada} -> ${salida}.`);
		}
		delete savingById[trackId];
		savingById = { ...savingById };
	}
	async function handleDelete(trackId: string, event: MouseEvent) {
		event.stopPropagation();
		const item = indeterminados[trackId];
		savingById[trackId] = true;
		savingById = { ...savingById };
		sortedIndeterminados = sortedIndeterminados.filter(([id]) => id !== trackId);
		if (item && activeBoundingBox === item.first_appearance.boundingBox) activeBoundingBox = null;
		playbackBoundingBoxes = playbackBoundingBoxes.filter((b) => b.id !== trackId);
		if (activeIndeterminateId === trackId) activeIndeterminateId = null;

		// Eliminar completamente de data_obj_history (no debe mostrarse más en el video ni contarse)
		if (generalTrackHistory.has(trackId)) {
			generalTrackHistory.delete(trackId);
			rebuildGeneralFrameMapFromTrackMap();
			// Si el video está pausado, refrescar overlays en el frame actual
			if (videoElement?.paused) updateOverlaysForCurrentFrame();
		}

		// Si estaba seleccionado, limpiar selección y rutas inmediatamente
		if (selectedTrackId === trackId) {
			selectedTrackId = null;
			selectedBoxRect = null;
			routePastPoints = [];
			routeFuturePoints = [];
			routeAllPoints = [];
			routePastSegments = [];
			routeFutureSegments = [];
			routeFadingOut = false;
			routeAnimating = false;
			if (routeAnimTimer) clearTimeout(routeAnimTimer);
			if (routeFadeTimer) clearTimeout(routeFadeTimer);
		}

		delete indeterminados[trackId];
		indeterminados = { ...indeterminados };

		const ok = await updateBackendData();
		if (ok) {
			showSuccess(`Vehículo indeterminado ${trackId} eliminado.`);
		}
		delete savingById[trackId];
		savingById = { ...savingById };
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
	let zoneItems = $derived.by(() => zoneIds.map((z) => ({ value: z, label: `Zona ${z}` })));
	let zoneItemsWithPlaceholder = $derived.by(() => [
		{ value: '', label: 'Seleccionar…' },
		...zoneItems
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

	// --- MERGE (Unir) de indeterminados ---
	function startMergeFrom(trackId: string) {
		if (mergeInProgress) return;
		mergeModeActive = true;
		mergeSourceId = trackId;
	}

	function cancelMergeMode() {
		mergeModeActive = false;
		mergeSourceId = null;
	}

	function recomputeSortedIndeterminados() {
		sortedIndeterminados = Object.entries(indeterminados).sort(([, a], [, b]) => {
			const aEntradaUnknown = isUnknownLabel(a.labels[0]);
			const aSalidaUnknown = isUnknownLabel(a.labels[1]);
			const bEntradaUnknown = isUnknownLabel(b.labels[0]);
			const bSalidaUnknown = isUnknownLabel(b.labels[1]);
			const aIsEntradaConocida = !aEntradaUnknown && aSalidaUnknown;
			const bIsEntradaConocida = !bEntradaUnknown && bSalidaUnknown;
			if (aIsEntradaConocida && !bIsEntradaConocida) return -1;
			if (!aIsEntradaConocida && bIsEntradaConocida) return 1;
			return parseInt(a.first_appearance.frame) - parseInt(b.first_appearance.frame);
		});
	}

	function rebuildGeneralFrameMapFromTrackMap() {
		const frameMap = new Map<number, GeneralBBox[]>();
		for (const [trackId, points] of generalTrackHistory.entries()) {
			for (const p of points) {
				if (!frameMap.has(p.frame)) frameMap.set(p.frame, []);
				frameMap.get(p.frame)!.push({ id: String(trackId), box: p.box });
			}
		}
		generalBBoxesByFrame = frameMap;
	}

	async function performMerge(keepId: string, removeId: string) {
		if (mergeInProgress) return false;
		mergeInProgress = true;
		try {
			const keep = indeterminados[keepId];
			const rem = indeterminados[removeId];
			if (!keep || !rem) {
				showError('No se encontraron ambos indeterminados.');
				return false;
			}

			// Actualizar labels priorizando el que queda, completando faltantes
			const [ke0, ks0] = keep.labels;
			const [re0, rs0] = rem.labels;
			const entrada = isUnknownLabel(ke0) && !isUnknownLabel(re0) ? re0 : ke0;
			const salida = isUnknownLabel(ks0) && !isUnknownLabel(rs0) ? rs0 : ks0;
			// Apariciones: elegir min frame para first y max para last
			const kFirst = parseInt(keep.first_appearance.frame);
			const rFirst = parseInt(rem.first_appearance.frame);
			const kLast = parseInt(keep.last_appearance.frame);
			const rLast = parseInt(rem.last_appearance.frame);
			const newFirst = kFirst <= rFirst ? keep.first_appearance : rem.first_appearance;
			const newLast = kLast >= rLast ? keep.last_appearance : rem.last_appearance;

			// Aplicar cambios al que queda
			indeterminados[keepId] = {
				...keep,
				labels: [entrada ?? '', salida ?? ''],
				first_appearance: newFirst,
				last_appearance: newLast
			};

			// Eliminar el que se fusiona
			delete indeterminados[removeId];
			indeterminados = { ...indeterminados };

			// Unir histories en data_obj_history (generalTrackHistory)
			const keepPts = (generalTrackHistory.get(keepId) || []).slice();
			const remPts = (generalTrackHistory.get(removeId) || []).slice();
			const byFrame = new Map<number, TrackPoint>();
			for (const p of keepPts) byFrame.set(p.frame, p);
			for (const p of remPts) if (!byFrame.has(p.frame)) byFrame.set(p.frame, p);
			const merged = Array.from(byFrame.values()).sort((a, b) => a.frame - b.frame);
			generalTrackHistory.set(keepId, merged);
			generalTrackHistory.delete(removeId);
			rebuildGeneralFrameMapFromTrackMap();

			// Limpiar overlays/selecciones
			playbackBoundingBoxes = playbackBoundingBoxes.filter((b) => b.id !== removeId);
			if (activeIndeterminateId === removeId) activeIndeterminateId = null;
			if (selectedTrackId === removeId) {
				selectedTrackId = keepId;
				updateOverlaysForCurrentFrame();
			}

			// Si tras unir queda determinado, confirmar automáticamente
			const nowDetermined = !isUnknownLabel(entrada) && !isUnknownLabel(salida);
			if (nowDetermined) {
				const vehiculo = indeterminados[keepId].class;
				if (rutas[entrada]?.[salida]?.[vehiculo] !== undefined) {
					rutas[entrada][salida][vehiculo]++;
				} else {
					if (!rutas[entrada]) rutas[entrada] = {} as any;
					if (!rutas[entrada][salida]) rutas[entrada][salida] = {} as any;
					vehicleTypes.forEach((v) => {
						if (rutas[entrada][salida][v] === undefined) rutas[entrada][salida][v] = 0;
					});
					rutas[entrada][salida][vehiculo] = (rutas[entrada][salida][vehiculo] ?? 0) + 1;
				}
				// mover a determinados
				determinados[keepId] = {
					...indeterminados[keepId],
					labels: [entrada, salida]
				};
				delete indeterminados[keepId];
				indeterminados = { ...indeterminados };
				determinados = { ...determinados };
				rutas = { ...rutas };
			}

			recomputeSortedIndeterminados();

			const ok = await updateBackendData();
			if (ok) {
				if (nowDetermined) {
					showSuccess(
						`Indeterminados ${keepId} y ${removeId} unidos y confirmado ${keepId} como ${entrada} → ${salida}.`
					);
				} else {
					showSuccess(`Indeterminados ${keepId} y ${removeId} unidos (se conserva ${keepId}).`);
				}
			}
			return ok;
		} finally {
			mergeInProgress = false;
		}
	}

	async function onIndeterminateCardClick(trackId: string, e: MouseEvent) {
		e.stopPropagation();
		if (mergeModeActive) {
			if (!mergeSourceId) return;
			if (mergeSourceId === trackId) {
				// cancelar si hace click sobre la misma tarjeta
				cancelMergeMode();
				return;
			}
			const a = parseInt(mergeSourceId);
			const b = parseInt(trackId);
			const keepId = String(Math.min(a, b));
			const removeId = String(Math.max(a, b));
			const proceed = await showConfirm({
				title: 'Unir indeterminados',
				message: `Se unirán los indeterminados ${keepId} y ${removeId}. El ID ${keepId} se mantendrá y el ${removeId} se eliminará.\n¿Desea continuar?`,
				variant: 'warning',
				confirmText: 'Unir',
				cancelText: 'Cancelar'
			});
			if (!proceed) {
				cancelMergeMode();
				return;
			}
			await performMerge(keepId, removeId);
			cancelMergeMode();
			return;
		}
		// comportamiento normal
		handleIndeterminateClick(trackId);
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
									// actualizar overlays mientras se busca estando en pausa
									if (videoElement.paused) updateOverlaysForCurrentFrame();
								}
							}}
							onseeked={() => {
								if (videoElement?.paused) updateOverlaysForCurrentFrame();
							}}
							ontimeupdate={() => {
								if (videoElement?.paused) updateOverlaysForCurrentFrame();
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
									style={`z-index: 13; opacity: ${routeFadingOut ? 0 : 1}; transition: opacity 0.5s ease;`}
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
					<h3 class="text-xl font-semibold mt-3 mb-2 text-center">Vehículos Indeterminados</h3>
					<div class="px-2 mb-3">
						<input
							bind:this={searchInputEl}
							type="text"
							placeholder="Buscar por ID  (Ctrl + K)"
							class="w-full px-3 py-2 rounded bg-transparent border outline-none focus:ring focus:ring-white/20"
							value={searchQuery}
							oninput={(e) => (searchQuery = (e.target as HTMLInputElement).value)}
						/>
					</div>

					<div class="overflow-y-auto flex-1">
						<div class="space-y-3 p-1">
							{#each visibleIndeterminados as [trackId, item] (trackId)}
								{@const labels = indeterminados[trackId]?.labels ?? ['', '']}
								{@const entrada = labels[0]}
								{@const salida = labels[1]}
								{@const isUnknown = (x: string) => !x || x === 'IND'}
								{@const canConfirm = !isUnknown(entrada) && !isUnknown(salida)}
								<div
									id={`ind-card-${trackId}`}
									class="ind-card"
									class:live={liveIndeterminateIds.has(trackId) ||
										trackId === activeIndeterminateId}
									role="button"
									tabindex="0"
									onclick={(e) => onIndeterminateCardClick(trackId, e)}
									onkeydown={(e) => handleKeyPress(e, trackId)}
								>
									<div class="flex justify-between items-center mb-2">
										<p class="font-bold text-lg">ID: {trackId}</p>
										<button
											onclick={(e) => handleDelete(trackId, e)}
											class="glass-button btn-danger text-xs py-1 px-2 disabled:opacity-60 disabled:cursor-not-allowed"
											disabled={savingById[trackId] || mergeModeActive || mergeInProgress}
										>
											{#if savingById[trackId]}
												<Spinner size={14} className="inline-block mr-1" />
												Eliminando...
											{:else}
												Eliminar
											{/if}
										</button>
									</div>
									<div class="grid grid-cols-4 gap-2 items-center mb-2 text-sm">
										<span class="text-gray-400">Clase:</span>
										<div class="col-span-3">
											<GlassSelect
												items={vehicleItems}
												value={indeterminados[trackId].class}
												ariaLabel={`Clase para ${trackId}`}
												stopClickPropagation={true}
												disabled={mergeModeActive || mergeInProgress}
												onChange={(val) => {
													indeterminados[trackId].class = String(val ?? '');
													indeterminados = { ...indeterminados };
												}}
											/>
										</div>
									</div>
									<div class="grid grid-cols-4 gap-2 items-center mb-3 text-sm">
										<span class="text-gray-400">Ruta:</span>
										<div class="col-span-3 flex items-center gap-1">
											<div class="w-full">
												<GlassSelect
													items={zoneItemsWithPlaceholder}
													value={indeterminados[trackId].labels[0] ?? ''}
													ariaLabel={`Entrada para ${trackId}`}
													stopClickPropagation={true}
													disabled={mergeModeActive || mergeInProgress}
													onChange={(val) => {
														const v = String(val ?? '');
														indeterminados[trackId].labels[0] = v; // dejar vacío si no hay selección
														indeterminados = { ...indeterminados };
													}}
												/>
											</div>
											<span class="text-gray-400">→</span>
											<div class="w-full">
												<GlassSelect
													items={zoneItemsWithPlaceholder}
													value={indeterminados[trackId].labels[1] ?? ''}
													ariaLabel={`Salida para ${trackId}`}
													stopClickPropagation={true}
													disabled={mergeModeActive || mergeInProgress}
													onChange={(val) => {
														const v = String(val ?? '');
														indeterminados[trackId].labels[1] = v; // dejar vacío si no hay selección
														indeterminados = { ...indeterminados };
													}}
												/>
											</div>
										</div>
										<!-- Botón Unir: debajo de los selects y ocupando columnas 2 a 4 -->
										<div class="col-start-2 col-span-3 mt-1">
											<button
												type="button"
												onclick={(e) => {
													e.stopPropagation();
													// Si ya está activo el modo Unir y esta NO es la tarjeta fuente, no hacer nada
													if (mergeModeActive && mergeSourceId !== trackId) {
														return;
													}
													if (mergeModeActive && mergeSourceId === trackId) {
														cancelMergeMode();
													} else {
														startMergeFrom(trackId);
													}
												}}
												class="merge-button w-full py-2 text-sm font-semibold rounded-xl disabled:opacity-60 disabled:cursor-not-allowed"
												class:merge-button--active={mergeModeActive && mergeSourceId === trackId}
												class:merge-button--no-hover={mergeModeActive}
												disabled={(mergeModeActive && mergeSourceId !== trackId) ||
													savingById[trackId] ||
													mergeInProgress}
											>
												{mergeModeActive && mergeSourceId === trackId ? 'Uniendo...' : '+ Unir'}
											</button>
										</div>
									</div>
									<button
										onclick={(e) => handleConfirm(trackId, e)}
										onmousedown={(e) => e.stopPropagation()}
										onmouseup={(e) => e.stopPropagation()}
										disabled={!canConfirm ||
											savingById[trackId] ||
											mergeModeActive ||
											mergeInProgress}
										class="w-full py-2 text-sm font-semibold rounded flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed glass-button"
										class:btn-success={canConfirm}
										class:btn-disabled={!canConfirm}
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
		transition:
			opacity 0.5s ease,
			box-shadow 0.5s ease;
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

	/* Botón "+ Unir" (fondo transparente, borde y letras blancas) */
	.merge-button {
		background-color: transparent;
		border: 1px solid #ffffff;
		color: #ffffff;
		transition:
			background-color 180ms ease,
			color 180ms ease,
			box-shadow 180ms ease,
			border-color 180ms ease;
	}
	.merge-button:hover {
		background-color: rgba(255, 255, 255, 0.08);
	}
	/* Desactivar hover en modo uniendo para todos los botones excepto el activo */
	.merge-button.merge-button--no-hover:not(.merge-button--active):hover {
		background-color: inherit;
	}
	/* Estado activo (cuando es la tarjeta fuente en modo Unir) */
	.merge-button--active {
		background-color: #ffffff;
		color: #000000;
		border-color: #ffffff;
		box-shadow:
			0 0 5px rgba(255, 255, 255, 0.8),
			0 0 10px rgba(255, 255, 255, 0.6),
			0 0 20px rgba(255, 255, 255, 0.4);
	}
	/* Asegurar que el botón activo no cambie con hover */
	.merge-button--active:hover {
		background-color: #ffffff;
		color: #000000;
		border-color: #ffffff;
		box-shadow:
			0 0 5px rgba(255, 255, 255, 0.8),
			0 0 10px rgba(255, 255, 255, 0.6),
			0 0 20px rgba(255, 255, 255, 0.4);
	}
</style>

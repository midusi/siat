<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { quintOut } from 'svelte/easing';
	import { fly, fade } from 'svelte/transition';
	import { page } from '$app/stores';
	import { apiFetch } from '$lib/api';
	import { goto } from '$app/navigation';
	import { showAlert } from '$lib/dialog';
	import Spinner from '$lib/components/Spinner.svelte';
	import GlassSelect from '$lib/components/GlassSelect.svelte';
	import ScrollArea from '$lib/components/ScrollArea.svelte';
	import {
		movePolygon,
		moveVertex,
		duplicatePolygon,
		isPointInPolygon,
		nearestVertexIndex,
		defaultColorForSentido,
		hexToRgba
	} from '$lib/polygon-utils';

	// --- Estado de la Carga de Datos ---
	let imageSrc: string = '';
	let isLoading: boolean = true;
	let errorMessage: string | null = null;
	let taskId: string;
	let frameWidth: number = 1920;
	let frameHeight: number = 1080;
	let videoWidth: number;
	let videoHeight: number;
	let imageB64: string;

	// --- Estado del Canvas y Dibujo ---
	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D;
	let imageRef: HTMLImageElement;
	let currentPoints: Array<{ x: number; y: number }> = [];

	// --- Estado de Polígonos ---
	let poligonos: Array<{
		id: number;
		via: string;
		sentido: string;
		vertices: Array<{ x: number; y: number }>;
		color?: string;
	}> = [];

	let _idCounter = 0;
	function newId() {
		_idCounter += 1;
		return Date.now() + _idCounter;
	}

	// --- Modos ---
	let modoZonaExcluida = false;
	let modoEdicion = false;

	function setModoZonaExcluida(flag: boolean) {
		if (modoZonaExcluida === flag) return;
		modoZonaExcluida = flag;
		currentPoints = [];
		if (pendingPolygon) cancelPendingPolygon();
		requestAnimationFrame(redrawCanvas);
	}

	function setModoEdicion(flag: boolean) {
		modoEdicion = flag;
		cursorStyle = flag ? 'default' : 'crosshair';
		if (flag) {
			if (pendingPolygon) cancelPendingPolygon();
			currentPoints = [];
		} else {
			selectedPolyId = null;
			endDrag();
		}
		requestAnimationFrame(redrawCanvas);
	}

	// --- Estado del Popover Contextual ---
	let pendingPolygon: {
		via: string;
		sentido: string;
		vertices: Array<{ x: number; y: number }>;
	} | null = null;
	let popoverPosition = { top: 0, left: 0, transform: 'translate(-50%, 15px)' };
	let popoverEl: HTMLDivElement | null = null;
	let viaInputEl: HTMLInputElement | null = null;

	// --- Estado de Edición (Selección / Arrastre) ---
	let selectedPolyId: number | null = null;
	let editingPolyId: number | null = null;
	let editValue: string = '';

	// Drag state
	let isDragging = false;
	let dragType: 'move' | 'vertex' | null = null;
	let dragPolyId: number | null = null;
	let dragVertexIndex: number = -1;
	let dragStartRelX: number = 0;
	let dragStartRelY: number = 0;
	let dragPolyOrigVertices: Array<{ x: number; y: number }> = [];

	// Cursor style (managed manually, not reactively)
	let cursorStyle = 'crosshair';

	// --- Estado de la Interfaz ---
	let isSubmitting = false;
	let entradasCount = 0;
	let salidasCount = 0;
	$: entradasCount = poligonos.filter((p) => p.sentido === 'Entrada').length;
	$: salidasCount = poligonos.filter((p) => p.sentido === 'Salida').length;
	$: canSubmit = entradasCount > 0 && salidasCount > 0 && !isSubmitting;

	// --- Opciones ---
	let opcionesSentido = ['Entrada', 'Salida'];
	let lastSentido: string = opcionesSentido[0];

	// --- Ciclo de vida y Eventos ---
	onMount(() => {
		const unsubscribePage = page.subscribe((p) => {
			taskId = p.params.id;
		});

		const fetchFirstFrame = async () => {
			if (!taskId) return;
			try {
				isLoading = true;
				errorMessage = null;
				const response = await apiFetch(`/task/${taskId}/get-first-frame-info`);
				if (!response.ok) {
					throw new Error(`Error al obtener información del primer frame: ${response.statusText}`);
				}
				const info = await response.json();
				videoWidth = info.width;
				videoHeight = info.height;
				imageB64 = info.image_b64;
				frameWidth = videoWidth;
				frameHeight = videoHeight;
				if (imageB64) {
					imageSrc = `data:image/jpeg;base64,${imageB64}`;
				} else {
					throw new Error('Respuesta sin imagen base64');
				}
			} catch (error) {
				console.error('No se pudo cargar el frame de la tarea:', error);
				errorMessage = 'No se pudo cargar la imagen. Por favor, recargue la página.';
			} finally {
				isLoading = false;
			}
		};

		fetchFirstFrame();

		window.addEventListener('keydown', handleKeyDown);
		window.addEventListener('mousemove', handleWindowMouseMove);
		window.addEventListener('mouseup', handleWindowMouseUp);

		const onResize = () => {
			setupCanvas();
			updatePopoverPositionForCurrentPending();
		};
		window.addEventListener('resize', onResize);

		onDestroy(() => {
			unsubscribePage();
			window.removeEventListener('keydown', handleKeyDown);
			window.removeEventListener('mousemove', handleWindowMouseMove);
			window.removeEventListener('mouseup', handleWindowMouseUp);
			window.removeEventListener('resize', onResize);
		});
	});

	function setupCanvas() {
		if (imageRef && imageRef.complete && imageRef.naturalWidth > 0 && canvas) {
			ctx = canvas.getContext('2d')!;
			canvas.width = imageRef.clientWidth;
			canvas.height = imageRef.clientHeight;
			requestAnimationFrame(redrawCanvas);
		}
	}

	// --- Lógica de Interacción: Dibujo ---

	function ordenarVertices(
		points: Array<{ x: number; y: number }>
	): Array<{ x: number; y: number }> {
		if (points.length < 3) return points;
		const n = points.length;
		const centro = points.reduce((acc, p) => ({ x: acc.x + p.x, y: acc.y + p.y }), {
			x: 0,
			y: 0
		});
		centro.x /= n;
		centro.y /= n;
		return points
			.map((point) => ({
				...point,
				angle: Math.atan2(point.y - centro.y, point.x - centro.x)
			}))
			.sort((a, b) => a.angle - b.angle)
			.map(({ x, y }) => ({ x, y }));
	}

	function calculatePopoverPosition(
		polyVerticesCanvasPx: Array<{ x: number; y: number }>,
		canvasRect: DOMRect,
		measuredWidth?: number,
		measuredHeight?: number
	) {
		const centro = polyVerticesCanvasPx.reduce((acc, v) => ({ x: acc.x + v.x, y: acc.y + v.y }), {
			x: 0,
			y: 0
		});
		centro.x /= 4;
		centro.y /= 4;
		const margin = 16;
		const offsetY = 15;
		const width = measuredWidth ?? popoverEl?.offsetWidth ?? 288;
		const height = measuredHeight ?? popoverEl?.offsetHeight ?? 230;
		let top = centro.y + canvasRect.top + offsetY;
		let transform = 'translate(-50%, 0)';
		if (top + height > window.innerHeight - margin) {
			top = centro.y + canvasRect.top - offsetY - height;
			transform = 'translate(-50%, 0)';
		}
		let left = centro.x + canvasRect.left;
		if (left + width / 2 > window.innerWidth - margin)
			left = window.innerWidth - width / 2 - margin;
		if (left - width / 2 < margin) left = width / 2 + margin;
		return { top, left, transform };
	}

	async function handleCanvasClick(event: MouseEvent) {
		// Edit mode handles canvas interaction via mousedown — ignore click here
		if (modoEdicion) return;
		if (pendingPolygon) return;
		const rect = canvas.getBoundingClientRect();
		const xCanvas = event.clientX - rect.left;
		const yCanvas = event.clientY - rect.top;
		currentPoints.push({ x: xCanvas / canvas.width, y: yCanvas / canvas.height });

		if (modoZonaExcluida) {
			requestAnimationFrame(redrawCanvas);
			return;
		}

		if (currentPoints.length === 4) {
			const verticesOrdenados = ordenarVertices(currentPoints);
			pendingPolygon = { vertices: verticesOrdenados, via: '', sentido: lastSentido };
			currentPoints = [];
			const absVerticesCanvas = verticesOrdenados.map((v) => ({
				x: v.x * canvas.width,
				y: v.y * canvas.height
			}));
			const { top, left, transform } = calculatePopoverPosition(absVerticesCanvas, rect);
			popoverPosition = { top, left, transform };
			await tick();
			const rect2 = canvas.getBoundingClientRect();
			const measured = calculatePopoverPosition(
				absVerticesCanvas,
				rect2,
				popoverEl?.offsetWidth ?? undefined,
				popoverEl?.offsetHeight ?? undefined
			);
			popoverPosition = measured;
			viaInputEl?.focus();
			viaInputEl?.select();
		}
		requestAnimationFrame(redrawCanvas);
	}

	async function handleKeyDown(event: KeyboardEvent) {
		if (pendingPolygon) {
			if (event.key === 'Enter') {
				if (pendingPolygon.via && pendingPolygon.via.trim().length > 0) confirmPendingPolygon();
			}
			if (event.key === 'Escape') cancelPendingPolygon();
			return;
		}
		if (modoZonaExcluida) {
			if (event.key === 'Enter') {
				if (currentPoints.length >= 3) {
					const verticesOrdenados = ordenarVertices(currentPoints);
					const nextIdx = poligonos.filter((p) => p.sentido === 'Excluida').length + 1;
					poligonos = [
						...poligonos,
						{
							id: newId(),
							via: `Zona excluída ${nextIdx}`,
							sentido: 'Excluida',
							vertices: verticesOrdenados
						}
					];
					currentPoints = [];
					await tick();
				}
			}
			if (event.key === 'Escape') currentPoints = [];
			if (event.key === 'Backspace') currentPoints.pop();
			requestAnimationFrame(redrawCanvas);
			return;
		}
		if (event.key === 'Escape') {
			currentPoints = [];
			if (modoEdicion) {
				selectedPolyId = null;
				requestAnimationFrame(redrawCanvas);
			}
		}
		if (event.key === 'Backspace' && !modoEdicion) currentPoints.pop();
		requestAnimationFrame(redrawCanvas);
	}

	function confirmPendingPolygon() {
		if (!pendingPolygon) return;
		lastSentido = pendingPolygon.sentido;
		poligonos = [
			...poligonos,
			{
				id: newId(),
				via: pendingPolygon.via.trim(),
				sentido: pendingPolygon.sentido,
				vertices: pendingPolygon.vertices
			}
		];
		pendingPolygon = null;
		requestAnimationFrame(redrawCanvas);
	}

	function cancelPendingPolygon() {
		pendingPolygon = null;
		requestAnimationFrame(redrawCanvas);
	}

	function eliminarPoligono(id: number) {
		poligonos = poligonos.filter((p) => p.id !== id);
		if (selectedPolyId === id) selectedPolyId = null;
		requestAnimationFrame(redrawCanvas);
	}

	// --- Lógica de Interacción: Edición (canvas) ---

	function handleCanvasMouseDown(event: MouseEvent) {
		if (!modoEdicion) return;
		// Prevent the browser's click event and text-selection drag
		event.preventDefault();

		const rect = canvas.getBoundingClientRect();
		const relX = (event.clientX - rect.left) / canvas.width;
		const relY = (event.clientY - rect.top) / canvas.height;

		// Check vertex handle hit on the currently selected polygon (higher priority)
		if (selectedPolyId !== null) {
			const poly = poligonos.find((p) => p.id === selectedPolyId);
			if (poly) {
				const vIdx = nearestVertexIndex(
					relX,
					relY,
					poly.vertices,
					15 / canvas.width,
					15 / canvas.height
				);
				if (vIdx >= 0) {
					isDragging = true;
					dragType = 'vertex';
					dragPolyId = selectedPolyId;
					dragVertexIndex = vIdx;
					cursorStyle = 'crosshair';
					return;
				}
			}
		}

		// Check polygon interior (iterate in reverse so topmost polygon wins)
		for (let i = poligonos.length - 1; i >= 0; i--) {
			const poly = poligonos[i];
			if (isPointInPolygon(relX, relY, poly.vertices)) {
				selectedPolyId = poly.id;
				isDragging = true;
				dragType = 'move';
				dragPolyId = poly.id;
				dragStartRelX = relX;
				dragStartRelY = relY;
				dragPolyOrigVertices = poly.vertices.map((v) => ({ ...v }));
				cursorStyle = 'grabbing';
				requestAnimationFrame(redrawCanvas);
				return;
			}
		}

		// Clicked empty space — deselect
		selectedPolyId = null;
		requestAnimationFrame(redrawCanvas);
	}

	function handleWindowMouseMove(event: MouseEvent) {
		if (isDragging && modoEdicion) {
			const rect = canvas?.getBoundingClientRect();
			if (!rect) return;
			const relX = (event.clientX - rect.left) / canvas.width;
			const relY = (event.clientY - rect.top) / canvas.height;

			if (dragType === 'move' && dragPolyId !== null) {
				const dx = relX - dragStartRelX;
				const dy = relY - dragStartRelY;
				poligonos = poligonos.map((p) =>
					p.id === dragPolyId ? { ...p, vertices: movePolygon(dragPolyOrigVertices, dx, dy) } : p
				);
			} else if (dragType === 'vertex' && dragPolyId !== null) {
				poligonos = poligonos.map((p) =>
					p.id === dragPolyId
						? { ...p, vertices: moveVertex(p.vertices, dragVertexIndex, relX, relY) }
						: p
				);
			}

			requestAnimationFrame(redrawCanvas);
		} else {
			updateCursor(event);
		}
	}

	function handleWindowMouseUp() {
		if (isDragging) endDrag();
	}

	function endDrag() {
		isDragging = false;
		dragType = null;
		dragPolyId = null;
		dragVertexIndex = -1;
		if (modoEdicion) cursorStyle = 'default';
	}

	function updateCursor(event: MouseEvent) {
		if (!modoEdicion || !canvas) return;
		const rect = canvas.getBoundingClientRect();
		const relX = (event.clientX - rect.left) / canvas.width;
		const relY = (event.clientY - rect.top) / canvas.height;

		// Out of canvas bounds
		if (relX < 0 || relX > 1 || relY < 0 || relY > 1) {
			cursorStyle = 'default';
			return;
		}

		// Vertex handle hit on selected polygon
		if (selectedPolyId !== null) {
			const poly = poligonos.find((p) => p.id === selectedPolyId);
			if (poly) {
				const vIdx = nearestVertexIndex(
					relX,
					relY,
					poly.vertices,
					15 / canvas.width,
					15 / canvas.height
				);
				if (vIdx >= 0) {
					cursorStyle = 'crosshair';
					return;
				}
			}
		}

		// Polygon interior
		for (let i = poligonos.length - 1; i >= 0; i--) {
			if (isPointInPolygon(relX, relY, poligonos[i].vertices)) {
				cursorStyle = 'grab';
				return;
			}
		}

		cursorStyle = 'default';
	}

	// --- Acciones de Edición (desde Sidebar) ---

	function duplicarPoligono(id: number) {
		const poly = poligonos.find((p) => p.id === id);
		if (!poly) return;
		const newVertices = duplicatePolygon(poly.vertices, 0.03, 0.03);
		poligonos = [
			...poligonos,
			{
				id: newId(),
				via: `${poly.via} (copia)`,
				sentido: poly.sentido,
				vertices: newVertices,
				color: poly.color
			}
		];
		requestAnimationFrame(redrawCanvas);
	}

	function cambiarColorPoligono(id: number, color: string) {
		poligonos = poligonos.map((p) => (p.id === id ? { ...p, color } : p));
		requestAnimationFrame(redrawCanvas);
	}

	async function iniciarRenombrado(id: number) {
		const poly = poligonos.find((p) => p.id === id);
		editValue = poly?.via ?? '';
		editingPolyId = id;
		await tick();
		const input = document.querySelector(`#rename-input-${id}`) as HTMLInputElement | null;
		input?.focus();
		input?.select();
	}

	function commitRename(id: number) {
		if (editValue.trim().length > 0) {
			poligonos = poligonos.map((p) => (p.id === id ? { ...p, via: editValue.trim() } : p));
		}
		editingPolyId = null;
		requestAnimationFrame(redrawCanvas);
	}

	function cancelRename() {
		editingPolyId = null;
	}

	// --- Envío ---

	async function finalizarProceso() {
		if (isSubmitting) return;
		if (entradasCount === 0 || salidasCount === 0) {
			await showAlert({
				message: 'Debes configurar al menos una entrada y una salida antes de continuar.',
				variant: 'warning'
			});
			return;
		}
		isSubmitting = true;
		const toAbs = (v: { x: number; y: number }) => [
			Math.round(v.x * frameWidth),
			Math.round(v.y * frameHeight)
		];
		const payload = {
			roads_in: poligonos
				.filter((p) => p.sentido === 'Entrada')
				.map((p) => ({ name: p.via.trim(), polygon: p.vertices.map(toAbs) })),
			roads_out: poligonos
				.filter((p) => p.sentido === 'Salida')
				.map((p) => ({ name: p.via.trim(), polygon: p.vertices.map(toAbs) })),
			excluded_zones: poligonos
				.filter((p) => p.sentido === 'Excluida')
				.map((p) => p.vertices.map(toAbs))
		};
		try {
			const response = await apiFetch(`/task/${taskId}/config`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			if (!response.ok) throw new Error('Error en el servidor');
			await response.json();
			await showAlert({ message: 'Vías guardadas correctamente.', variant: 'success' });
			goto('/');
		} catch (error) {
			console.error('Fallo al enviar los datos:', error);
			await showAlert({
				message: 'Hubo un error al guardar las vías. Inténtalo de nuevo.',
				variant: 'danger'
			});
		} finally {
			isSubmitting = false;
		}
	}

	// --- Función Central de Dibujo ---

	function redrawCanvas() {
		if (!ctx) return;
		ctx.clearRect(0, 0, canvas.width, canvas.height);

		// Draw non-excluded polygons first, then excluded (so excluded renders on top)
		poligonos
			.filter((p) => p.sentido !== 'Excluida')
			.forEach((poly) =>
				drawPolygonRel(poly, { confirmed: true, selected: poly.id === selectedPolyId })
			);
		poligonos
			.filter((p) => p.sentido === 'Excluida')
			.forEach((poly) =>
				drawPolygonRel(poly, { confirmed: true, selected: poly.id === selectedPolyId })
			);

		// Vertex handles for selected polygon (edit mode only)
		if (selectedPolyId !== null && modoEdicion) {
			const selectedPoly = poligonos.find((p) => p.id === selectedPolyId);
			if (selectedPoly) drawVertexHandles(selectedPoly);
		}

		// Pending polygon (awaiting name/direction confirmation)
		if (pendingPolygon) drawPolygonRel(pendingPolygon, { pending: true });

		// In-progress click points
		if (currentPoints.length > 0) {
			ctx.beginPath();
			const absPoints = currentPoints.map((p) => ({
				x: p.x * canvas.width,
				y: p.y * canvas.height
			}));
			ctx.moveTo(absPoints[0].x, absPoints[0].y);
			for (const p of absPoints.slice(1)) ctx.lineTo(p.x, p.y);
			ctx.strokeStyle = modoZonaExcluida ? 'rgba(0, 0, 0, 1)' : 'rgba(255, 255, 255, 0.8)';
			ctx.lineWidth = 2;
			ctx.setLineDash([6, 6]);
			ctx.stroke();
			ctx.setLineDash([]);
			absPoints.forEach((p) => {
				ctx.fillStyle = modoZonaExcluida ? 'rgba(0, 0, 0, 1)' : 'rgba(255, 255, 255, 1)';
				ctx.beginPath();
				ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
				ctx.fill();
			});
		}
	}

	function updatePopoverPositionForCurrentPending() {
		if (!pendingPolygon || !canvas) return;
		const rect = canvas.getBoundingClientRect();
		const absVerticesCanvas = pendingPolygon.vertices.map((v) => ({
			x: v.x * canvas.width,
			y: v.y * canvas.height
		}));
		const measured = calculatePopoverPosition(
			absVerticesCanvas,
			rect,
			popoverEl?.offsetWidth ?? undefined,
			popoverEl?.offsetHeight ?? undefined
		);
		popoverPosition = measured;
	}

	function drawPolygonRel(
		poly: {
			id?: number;
			via: string;
			sentido: string;
			vertices: Array<{ x: number; y: number }>;
			color?: string;
		},
		options: { confirmed?: boolean; pending?: boolean; selected?: boolean }
	) {
		const absVertices = poly.vertices.map((v) => ({
			x: v.x * canvas.width,
			y: v.y * canvas.height
		}));
		const isExcluded = poly.sentido === 'Excluida';

		// Use custom color if set, otherwise fall back to defaults by sentido
		const effectiveHex = isExcluded
			? '#000000'
			: (poly.color ?? defaultColorForSentido(poly.sentido));
		const solidColor = isExcluded ? 'rgba(0,0,0,1)' : hexToRgba(effectiveHex, 1);
		const fillAlpha = options.pending ? 0.5 : 0.3;
		const fillColor = isExcluded ? 'rgba(0,0,0,1)' : hexToRgba(effectiveHex, fillAlpha);

		// Fill
		ctx.fillStyle = fillColor;
		ctx.beginPath();
		ctx.moveTo(absVertices[0].x, absVertices[0].y);
		for (const v of absVertices.slice(1)) ctx.lineTo(v.x, v.y);
		ctx.closePath();
		ctx.fill();

		// Primary stroke
		ctx.strokeStyle = solidColor;
		ctx.lineWidth = options.pending ? 4 : 2;
		if (options.pending) ctx.setLineDash([8, 4]);
		ctx.stroke();
		ctx.setLineDash([]);

		// Selection indicator: dashed white outline drawn on top
		if (options.selected && !options.pending) {
			ctx.beginPath();
			ctx.moveTo(absVertices[0].x, absVertices[0].y);
			for (const v of absVertices.slice(1)) ctx.lineTo(v.x, v.y);
			ctx.closePath();
			ctx.strokeStyle = 'rgba(255,255,255,0.85)';
			ctx.lineWidth = 2;
			ctx.setLineDash([5, 3]);
			ctx.stroke();
			ctx.setLineDash([]);
		}

		// Label in centre
		if (options.confirmed) {
			const centro = absVertices.reduce((acc, v) => ({ x: acc.x + v.x, y: acc.y + v.y }), {
				x: 0,
				y: 0
			});
			const n = absVertices.length || 1;
			centro.x /= n;
			centro.y /= n;
			ctx.font = 'bold 14px sans-serif';
			ctx.fillStyle = 'white';
			ctx.textAlign = 'center';
			ctx.textBaseline = 'middle';
			ctx.shadowColor = 'black';
			ctx.shadowBlur = 5;
			ctx.fillText(poly.via, centro.x, centro.y);
			ctx.shadowBlur = 0;
		}
	}

	/** Draw resize handles (white circles with colored border) at each vertex. */
	function drawVertexHandles(poly: {
		vertices: Array<{ x: number; y: number }>;
		sentido: string;
		color?: string;
	}) {
		const handleColor = poly.color ?? defaultColorForSentido(poly.sentido);
		poly.vertices.forEach((v) => {
			const px = v.x * canvas.width;
			const py = v.y * canvas.height;
			ctx.beginPath();
			ctx.arc(px, py, 8, 0, Math.PI * 2);
			ctx.fillStyle = 'white';
			ctx.fill();
			ctx.strokeStyle = handleColor;
			ctx.lineWidth = 2;
			ctx.stroke();
		});
	}

	$: if (pendingPolygon) requestAnimationFrame(redrawCanvas);

	function goBack() {
		goto('/');
	}
</script>

<div class="page-container page-vertical">
	<div class="mx-auto flex flex-col flex-1 min-h-0 h-full">
		<!-- Título y descripción generales -->
		<div class="mb-2">
			<h1 class="heading-1">Asignar Vías</h1>
			<div class="mt-2 flex items-center justify-between gap-4 flex-wrap">
				<p class="text-white/70 text-sm m-0">
					<span class="swap-container">
						<span class="swap-measure">
							{#if modoEdicion}
								Clic en una zona para seleccionarla. Arrastre para moverla. Arrastre un vértice
								(círculo blanco) para redimensionarla. <kbd class="key-kbd">Esc</kbd> para deseleccionar.
							{:else if !modoZonaExcluida}
								Haga clic 4 veces en la imagen para definir una vía de entrada/salida. Use
								<kbd class="key-kbd">Backspace</kbd> para deshacer o
								<kbd class="key-kbd">Esc</kbd> para cancelar.
							{:else}
								Haga clic para agregar vértices y presione <kbd class="key-kbd">Enter</kbd> para
								confirmar una zona excluída (mín. 3 puntos). Use
								<kbd class="key-kbd">Backspace</kbd> para deshacer o
								<kbd class="key-kbd">Esc</kbd> para cancelar.
							{/if}
						</span>
						{#if modoEdicion}
							<span class="swap-layer" transition:fade={{ duration: 210 }}>
								Clic en una zona para seleccionarla. Arrastre para moverla. Arrastre un vértice
								(círculo blanco) para redimensionarla. <kbd class="key-kbd">Esc</kbd> para deseleccionar.
							</span>
						{:else if !modoZonaExcluida}
							<span class="swap-layer" transition:fade={{ duration: 210 }}>
								Haga clic 4 veces en la imagen para definir una vía de entrada/salida. Use
								<kbd class="key-kbd">Backspace</kbd> para deshacer o
								<kbd class="key-kbd">Esc</kbd> para cancelar.
							</span>
						{:else}
							<span class="swap-layer" transition:fade={{ duration: 210 }}>
								Haga clic para agregar vértices y presione <kbd class="key-kbd">Enter</kbd> para
								confirmar una zona excluída (mín. 3 puntos). Use
								<kbd class="key-kbd">Backspace</kbd> para deshacer o
								<kbd class="key-kbd">Esc</kbd> para cancelar.
							</span>
						{/if}
					</span>
				</p>
				<div class="flex items-center gap-2 flex-wrap">
					<!-- Toggle de modos: Entradas/Salidas vs Zonas Excluidas (disabled in edit mode) -->
					<div
						class="mode-toggle"
						role="group"
						aria-label="Modo de dibujo"
						class:opacity-50={modoEdicion}
						class:pointer-events-none={modoEdicion}
					>
						<div
							class={`mode-indicator ${modoZonaExcluida ? 'right bg-excluded' : 'left bg-inout'}`}
							aria-hidden="true"
						></div>
						<button
							class="mode-option left"
							disabled={!modoZonaExcluida || modoEdicion}
							aria-pressed={!modoZonaExcluida}
							onclick={() => setModoZonaExcluida(false)}
							title="Dibujar entradas/salidas"
						>
							<span class="swap-container">
								<span class="swap-measure">
									{#if !modoZonaExcluida}Dibujando entradas/salidas...{:else}Dibujar
										entradas/salidas{/if}
								</span>
								{#if !modoZonaExcluida}
									<span class="swap-layer" transition:fade={{ duration: 210 }}
										>Dibujando entradas/salidas...</span
									>
								{:else}
									<span class="swap-layer" transition:fade={{ duration: 210 }}
										>Dibujar entradas/salidas</span
									>
								{/if}
							</span>
						</button>
						<button
							class="mode-option right"
							disabled={modoZonaExcluida || modoEdicion}
							aria-pressed={modoZonaExcluida}
							onclick={() => setModoZonaExcluida(true)}
							title="Dibujar zonas excluidas (confirme con Enter)"
						>
							<span class="swap-container">
								<span class="swap-measure">
									{#if modoZonaExcluida}Dibujando zonas excluidas...{:else}Dibujar zonas excluidas{/if}
								</span>
								{#if modoZonaExcluida}
									<span class="swap-layer" transition:fade={{ duration: 210 }}
										>Dibujando zonas excluidas...</span
									>
								{:else}
									<span class="swap-layer" transition:fade={{ duration: 210 }}
										>Dibujar zonas excluidas</span
									>
								{/if}
							</span>
						</button>
					</div>

					<!-- Botón Mover/Redimensionar (modo edición canvas) -->
					<button
						class="glass-button px-3 py-2 flex items-center gap-1.5 border-white/20"
						class:bg-blue-500={modoEdicion}
						class:bg-opacity-30={modoEdicion}
						class:border-blue-400={modoEdicion}
						class:border-opacity-60={modoEdicion}
						class:bg-white-10={!modoEdicion}
						class:hover-bg-white-20={!modoEdicion}
						onclick={() => setModoEdicion(!modoEdicion)}
						title={modoEdicion
							? 'Salir del modo edición'
							: 'Mover y redimensionar zonas existentes'}
						aria-pressed={modoEdicion}
					>
						<!-- Move icon (4-arrow cross) -->
						<svg
							xmlns="http://www.w3.org/2000/svg"
							width="15"
							height="15"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
						>
							<polyline points="5 9 2 12 5 15" />
							<polyline points="9 5 12 2 15 5" />
							<polyline points="15 19 12 22 9 19" />
							<polyline points="19 9 22 12 19 15" />
							<line x1="2" y1="12" x2="22" y2="12" />
							<line x1="12" y1="2" x2="12" y2="22" />
						</svg>
						{modoEdicion ? 'Editando...' : 'Mover/Redimensionar'}
					</button>

					<button
						class="glass-button px-3 py-2 border-white/20 bg-white/10 hover:bg-white/20"
						onclick={goBack}
						aria-label="Volver"
					>
						← Volver
					</button>
				</div>
			</div>
		</div>

		<!-- Contenedor Principal con Layout de Grid: sidebar fijo + imagen máxima -->
		<div
			class="lg:grid lg:grid-cols-[320px_1fr] lg:gap-6 items-start flex-1 min-h-0 overflow-y-auto"
		>
			<!-- Columna Izquierda: Lista de Vías y Botón de Finalizar -->
			<div
				class="flex flex-col h-full max-h-full min-h-0 overflow-hidden glass-card p-4 lg:mr-4 mb-8 lg:mb-0"
			>
				<div class="flex items-center justify-between mb-4 gap-2">
					<h2 class="heading-2">Vías Definidas ({poligonos.length})</h2>
				</div>
				<!-- Área desplazable de la lista (con scrollbar custom) -->
				<ScrollArea orientation="y" className="flex-1 min-h-0 pr-1" autoHide>
					{#if poligonos.length === 0}
						<p class="text-white/70 text-center py-4 glass-surface rounded-lg">
							No hay vías definidas.
						</p>
					{:else}
						<div class="space-y-3">
							{#each poligonos as poly (poly.id)}
								<div
									class="glass-surface p-3 rounded-lg transition-all border"
									class:border-green-400={poly.sentido === 'Entrada'}
									class:border-red-400={poly.sentido === 'Salida'}
									class:border-white-30={poly.sentido === 'Excluida'}
									class:ring-2={poly.id === selectedPolyId}
									class:ring-white={poly.id === selectedPolyId}
									class:ring-opacity-50={poly.id === selectedPolyId}
									out:fly={{ y: -10, opacity: 0, duration: 250, easing: quintOut }}
								>
									<!-- Top row: color swatch + name + actions -->
									<div class="flex items-center gap-2">
										<!-- Color picker (hidden input triggered by swatch) -->
										<label
											class="cursor-pointer flex-shrink-0"
											title="Cambiar color de la zona"
											aria-label="Cambiar color"
										>
											<div
												class="w-5 h-5 rounded-full border border-white/40 flex-shrink-0"
												style="background-color: {poly.color ??
													defaultColorForSentido(poly.sentido)};"
											></div>
											<input
												type="color"
												class="sr-only"
												value={poly.color ?? defaultColorForSentido(poly.sentido)}
												oninput={(e) => cambiarColorPoligono(poly.id, e.currentTarget.value)}
											/>
										</label>

										<!-- Name (editable inline on demand) -->
										<div class="flex-1 min-w-0">
											{#if editingPolyId === poly.id}
												<input
													id="rename-input-{poly.id}"
													class="glass-input text-sm py-0.5 px-2 w-full"
													bind:value={editValue}
													onblur={() => commitRename(poly.id)}
													onkeydown={(e) => {
														if (e.key === 'Enter') commitRename(poly.id);
														if (e.key === 'Escape') cancelRename();
													}}
												/>
											{:else}
												<p class="font-semibold text-base truncate" title={poly.via}>{poly.via}</p>
											{/if}
										</div>

										<!-- Action buttons -->
										<div class="flex items-center gap-1 flex-shrink-0">
											<!-- Rename -->
											<button
												onclick={() => iniciarRenombrado(poly.id)}
												class="glass-button p-1.5"
												title="Renombrar"
												aria-label="Renombrar vía"
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													width="14"
													height="14"
													viewBox="0 0 24 24"
													fill="none"
													stroke="currentColor"
													stroke-width="2"
													stroke-linecap="round"
													stroke-linejoin="round"
													aria-hidden="true"
												>
													<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
													<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
												</svg>
											</button>
											<!-- Duplicate -->
											<button
												onclick={() => duplicarPoligono(poly.id)}
												class="glass-button p-1.5"
												title="Duplicar zona"
												aria-label="Duplicar vía"
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													width="14"
													height="14"
													viewBox="0 0 24 24"
													fill="none"
													stroke="currentColor"
													stroke-width="2"
													stroke-linecap="round"
													stroke-linejoin="round"
													aria-hidden="true"
												>
													<rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
													<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
												</svg>
											</button>
											<!-- Delete -->
											<button
												onclick={() => eliminarPoligono(poly.id)}
												class="glass-button btn-danger p-1.5"
												aria-label="Eliminar vía"
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													width="14"
													height="14"
													viewBox="0 0 24 24"
													fill="none"
													stroke="currentColor"
													stroke-width="2"
													stroke-linecap="round"
													stroke-linejoin="round"
													aria-hidden="true"
												>
													<polyline points="3 6 5 6 21 6" />
													<path
														d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
													/>
													<line x1="10" y1="11" x2="10" y2="17" />
													<line x1="14" y1="11" x2="14" y2="17" />
												</svg>
											</button>
										</div>
									</div>

									<!-- Sentido badge -->
									<p
										class="text-sm mt-1 ml-7"
										class:text-green-300={poly.sentido === 'Entrada'}
										class:text-red-300={poly.sentido === 'Salida'}
										class:text-white-60={poly.sentido === 'Excluida'}
									>
										{poly.sentido}
									</p>
								</div>
							{/each}
						</div>
					{/if}
				</ScrollArea>
				<!-- Botón Finalizar -->
				<div class="mt-auto pt-8">
					<button
						onclick={finalizarProceso}
						disabled={!canSubmit}
						title={!canSubmit && !isSubmitting
							? 'Requiere al menos 1 entrada y 1 salida'
							: undefined}
						class="w-full glass-button btn-success py-3 text-base flex items-center justify-center gap-2"
					>
						{#if isSubmitting}
							<Spinner size={20} />
							Guardando...
						{:else}
							Finalizar y Procesar
						{/if}
					</button>
				</div>
			</div>

			<!-- Columna Derecha: Imagen y Canvas (ocupa todo el ancho disponible) -->
			<div class="mt-8 lg:mt-0 w-full min-h-0">
				{#if isLoading}
					<div
						class="glass-card overflow-hidden shadow-2xl flex items-center justify-center text-white/90"
						style="aspect-ratio: {frameWidth} / {frameHeight};"
					>
						<div class="flex items-center gap-3">
							<Spinner size={24} />
							Cargando imagen...
						</div>
					</div>
				{:else if errorMessage}
					<div
						class="glass-card overflow-hidden shadow-2xl flex items-center justify-center border border-red-600/40 text-red-200 p-4"
						style="aspect-ratio: {frameWidth} / {frameHeight};"
					>
						{errorMessage}
					</div>
				{:else}
					<div
						class="canvas-container glass-card overflow-hidden shadow-2xl"
						style="cursor: {modoEdicion ? cursorStyle : 'crosshair'};"
						onclick={handleCanvasClick}
						onmousedown={handleCanvasMouseDown}
						role="button"
						tabindex="0"
						onkeydown={() => {}}
						aria-label={modoEdicion
							? 'Seleccionar y editar zona en la imagen'
							: modoZonaExcluida
								? 'Definir zona excluída en la imagen'
								: 'Definir entrada/salida en la imagen'}
					>
						<img
							src={imageSrc}
							alt="Imagen base"
							bind:this={imageRef}
							onload={() => {
								setupCanvas();
								isLoading = false;
							}}
							class="w-full h-auto opacity-100 prevent-drag"
							draggable="false"
						/>
						<canvas bind:this={canvas}></canvas>
					</div>
				{/if}
			</div>
		</div>
	</div>

	<!-- Popover Contextual para Confirmar Polígono -->
	{#if pendingPolygon}
		<div
			class="popover glass-strong frost frost-polarized p-4 w-72 border shadow-2xl"
			style="top: {popoverPosition.top}px; left: {popoverPosition.left}px; transform: {popoverPosition.transform};"
			bind:this={popoverEl}
			transition:fly={{ y: 20, duration: 250, easing: quintOut }}
		>
			<h3 class="font-semibold text-center text-lg mb-3">Confirmar Zona</h3>
			<div class="space-y-3">
				<div>
					<label for="via-input" class="block mb-1 text-sm text-white/80">Vía (obligatorio):</label>
					<input
						id="via-input"
						type="text"
						bind:value={pendingPolygon.via}
						bind:this={viaInputEl}
						class="glass-input"
						placeholder="Nombre de la vía"
						required
					/>
				</div>
				<div>
					<label for="sentido-select" class="block mb-1 text-sm text-white/80">Sentido:</label>
					<GlassSelect
						id="sentido-select"
						items={opcionesSentido.map((s) => ({ value: s, label: s }))}
						value={pendingPolygon.sentido}
						onChange={(v) => (pendingPolygon!.sentido = String(v))}
					/>
				</div>
			</div>
			<div class="flex gap-2 pt-4">
				<button onclick={cancelPendingPolygon} class="glass-button">Cancelar (Esc)</button>
				<button
					onclick={() => {
						if (pendingPolygon?.via && pendingPolygon.via.trim().length > 0) {
							confirmPendingPolygon();
						}
					}}
					class="glass-button btn-success"
					disabled={!pendingPolygon.via || pendingPolygon.via.trim().length === 0}
					>Confirmar (Enter)</button
				>
			</div>
		</div>
	{/if}
</div>

<style>
	.page-container {
		max-width: 95% !important;
		padding-left: 0 !important;
		padding-right: 0 !important;
	}
	.page-container > .mx-auto {
		margin-left: 0 !important;
		margin-right: 0 !important;
		max-width: none !important;
		width: 95% !important;
	}
	.page-vertical {
		display: flex;
		flex-direction: column;
		min-height: calc(
			100vh - var(--layout-gap, 0px) - var(--header-height, 0px) - var(--layout-gap, 0px) -
				var(--layout-bottom-gap, 0px) - var(--layout-bottom-gap, 0px) - var(--layout-gap, 0px)
		);
	}
	.canvas-container {
		position: relative;
		width: 100%;
		line-height: 0;
	}
	canvas {
		position: absolute;
		top: 0;
		left: 0;
		pointer-events: none;
	}
	.popover {
		position: fixed;
		z-index: 50;
	}
	.prevent-drag {
		user-select: none;
		-webkit-user-drag: none;
	}

	.key-kbd {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 600;
		color: #1f2937;
		background-color: #f3f4f6;
		border: 1px solid #e5e7eb;
		border-radius: 0.5rem;
	}

	.swap-container {
		position: relative;
		display: inline-block;
		vertical-align: middle;
	}
	.swap-measure {
		visibility: hidden;
		pointer-events: none;
	}
	.swap-layer {
		position: absolute;
		top: 0;
		left: 0;
		white-space: nowrap;
	}

	/* Toggle de modos */
	.mode-toggle {
		position: relative;
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0;
		align-items: center;
		background: transparent;
		border: 1px solid rgba(255, 255, 255, 0.25);
		border-radius: 12px;
		overflow: hidden;
		min-width: 420px;
		height: 40px;
	}
	.mode-option {
		position: relative;
		z-index: 1;
		background: transparent;
		border: none;
		outline: none;
		color: white;
		font-weight: 600;
		font-size: 0.9rem;
		padding: 0 16px;
		height: 100%;
		cursor: pointer;
	}
	.mode-option:disabled {
		cursor: default;
	}
	.mode-indicator {
		position: absolute;
		top: -1px;
		left: -1px;
		height: calc(100% + 2px);
		width: calc(50% + 2px);
		border: 1px solid rgba(255, 255, 255, 0.65);
		border-radius: 12px;
		box-shadow:
			0 0 0 2px rgba(255, 255, 255, 0.12),
			0 8px 24px rgba(0, 0, 0, 0.35);
		transition:
			transform 420ms cubic-bezier(0.22, 1, 0.36, 1),
			background 260ms ease;
		will-change: transform;
	}
	.mode-indicator.left {
		transform: translateX(0%);
	}
	.mode-indicator.right {
		transform: translateX(100%);
	}
	.bg-inout {
		background: linear-gradient(
			90deg,
			rgba(74, 222, 128, 0.35) 0%,
			rgba(74, 222, 128, 0.35) 40%,
			rgba(248, 113, 113, 0.35) 60%,
			rgba(248, 113, 113, 0.35) 100%
		);
		backdrop-filter: blur(8px) saturate(140%);
		-webkit-backdrop-filter: blur(8px) saturate(140%);
		border-color: transparent;
		box-shadow: 0 10px 28px rgba(0, 0, 0, 0.4);
	}
	.bg-excluded {
		background: rgba(0, 0, 0, 0.9);
	}

	@media (max-width: 640px) {
		.mode-toggle {
			min-width: 300px;
			font-size: 0.85rem;
		}
	}
</style>

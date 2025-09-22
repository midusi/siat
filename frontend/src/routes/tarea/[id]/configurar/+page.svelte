<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { tick } from 'svelte';
	import { quintOut } from 'svelte/easing';
	import { fly, fade } from 'svelte/transition';
	import { page } from '$app/stores';
	import { BACKEND_URL } from '$lib/constants';
	import { apiFetch } from '$lib/api';
	import { goto } from '$app/navigation';
	import { showAlert } from '$lib/dialog';
	import Spinner from '$lib/components/Spinner.svelte';
	import GlassSelect from '$lib/components/GlassSelect.svelte';
	import ScrollArea from '$lib/components/ScrollArea.svelte';

	// --- Estado de la Carga de Datos ---
	let imageSrc: string = '';
	let isLoading: boolean = true;
	let errorMessage: string | null = null;
	let taskId: string;
	// Dimensiones originales del frame
	let frameWidth: number = 1920;
	let frameHeight: number = 1080;

	// Variables para la información del primer frame
	let videoWidth: number;
	let videoHeight: number;
	let imageB64: string;

	// --- Estado del Canvas y Dibujo ---
	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D;
	let imageRef: HTMLImageElement;
	// Los puntos se guardan como relativos (0-1)
	let currentPoints: Array<{ x: number; y: number }> = [];

	// --- Estado de Polígonos ---
	// Los vértices ahora son relativos (0-1)
	let poligonos: Array<{
		id: number;
		via: string;
		sentido: string;
		vertices: Array<{ x: number; y: number }>;
	}> = [];

	// IDs únicos para claves estables en listas
	let _idCounter = 0;
	function newId() {
		_idCounter += 1;
		return Date.now() + _idCounter;
	}

	// Modo para agregar zonas excluidas
	let modoZonaExcluida = false; // página inicia en modo Entradas/Salidas

	function setModoZonaExcluida(flag: boolean) {
		if (modoZonaExcluida === flag) return;
		modoZonaExcluida = flag;
		// Al cambiar de modo, limpiar puntos actuales y cualquier polígono pendiente
		currentPoints = [];
		if (pendingPolygon) cancelPendingPolygon();
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

	// --- Estado de la Interfaz ---
	let isSubmitting = false; // Para deshabilitar el botón "Finalizar" durante el envío

	// Reglas de validación para finalizar: al menos 1 Entrada y 1 Salida
	let entradasCount = 0;
	let salidasCount = 0;
	$: entradasCount = poligonos.filter((p) => p.sentido === 'Entrada').length;
	$: salidasCount = poligonos.filter((p) => p.sentido === 'Salida').length;
	$: canSubmit = entradasCount > 0 && salidasCount > 0 && !isSubmitting;

	// --- Opciones ---
	// Via ahora es texto libre; mantener únicamente los sentidos predefinidos
	let opcionesSentido = ['Entrada', 'Salida'];
	// Recordar el último "Sentido" elegido para preseleccionarlo en el siguiente polígono
	let lastSentido: string = opcionesSentido[0];

	// --- Ciclo de vida y Eventos ---
	onMount(() => {
		const unsubscribePage = page.subscribe((p) => {
			taskId = p.params.id;
		});

		// Función para obtener el primer frame del video desde el backend
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
				// Actualizar dimensiones del frame usadas para las transformaciones
				frameWidth = videoWidth;
				frameHeight = videoHeight;
				// Construir el src de la imagen desde el base64 recibido
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

		// Los listeners se mantienen, pero la inicialización del canvas ahora es más robusta.
		window.addEventListener('keydown', handleKeyDown);
		const onResize = () => {
			setupCanvas();
			updatePopoverPositionForCurrentPending();
		};
		window.addEventListener('resize', onResize);

		onDestroy(() => {
			unsubscribePage(); // Limpiar la suscripción
			window.removeEventListener('keydown', handleKeyDown);
			window.removeEventListener('resize', onResize);
		});
	});

	function setupCanvas() {
		if (imageRef && imageRef.complete && imageRef.naturalWidth > 0 && canvas) {
			ctx = canvas.getContext('2d')!;
			// Usamos clientWidth/clientHeight para que el canvas tenga el tamaño visual de la imagen
			canvas.width = imageRef.clientWidth;
			canvas.height = imageRef.clientHeight;
			requestAnimationFrame(redrawCanvas); // Redibujar todo con las dimensiones correctas
		}
	}

	// --- Lógica de Interacción ---

	function ordenarVertices(
		points: Array<{ x: number; y: number }>
	): Array<{ x: number; y: number }> {
		// Ordena los puntos alrededor del centro por ángulo polar.
		// Funciona para N>=3 y evita polígonos auto-intersectados por orden incorrecto de clics.
		if (points.length < 3) return points;
		const n = points.length;
		const centro = points.reduce((acc, p) => ({ x: acc.x + p.x, y: acc.y + p.y }), { x: 0, y: 0 });
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
		const width = measuredWidth ?? popoverEl?.offsetWidth ?? 288; // fallback to w-72
		const height = measuredHeight ?? popoverEl?.offsetHeight ?? 230; // sensible default

		// Default: show below
		let top = centro.y + canvasRect.top + offsetY;
		let transform = 'translate(-50%, 0)';

		// If it would overflow bottom, flip above using measured height
		if (top + height > window.innerHeight - margin) {
			top = centro.y + canvasRect.top - offsetY - height;
			transform = 'translate(-50%, 0)';
		}

		// Horizontal clamping
		let left = centro.x + canvasRect.left;
		if (left + width / 2 > window.innerWidth - margin) {
			left = window.innerWidth - width / 2 - margin;
		}
		if (left - width / 2 < margin) {
			left = width / 2 + margin;
		}

		return { top, left, transform };
	}

	async function handleCanvasClick(event: MouseEvent) {
		if (pendingPolygon) return;
		const rect = canvas.getBoundingClientRect();
		// Convertir a coordenadas relativas al frame original
		const xCanvas = event.clientX - rect.left;
		const yCanvas = event.clientY - rect.top;
		// Relativo al tamaño actual del canvas
		const xRel = (xCanvas * frameWidth) / canvas.width / frameWidth;
		const yRel = (yCanvas * frameHeight) / canvas.height / frameHeight;
		// Simplifica: xRel = xCanvas / canvas.width, pero guardamos la relación con frameWidth
		currentPoints.push({ x: xCanvas / canvas.width, y: yCanvas / canvas.height });

		// En modo zona excluida, no mostramos popover, se confirma con Enter y permite N puntos
		if (modoZonaExcluida) {
			requestAnimationFrame(redrawCanvas);
			return;
		}

		if (currentPoints.length === 4) {
			const verticesOrdenados = ordenarVertices(currentPoints);
			pendingPolygon = {
				vertices: verticesOrdenados,
				via: '',
				sentido: lastSentido
			};
			currentPoints = [];
			// Para el popover, convertir a absolutas para posicionar
			const absVertices = verticesOrdenados.map((v) => ({
				x: v.x * frameWidth,
				y: v.y * frameHeight
			}));
			// Escalar a canvas actual para mostrar el popover
			const absVerticesCanvas = absVertices.map((v) => ({
				x: (v.x * canvas.width) / frameWidth,
				y: (v.y * canvas.height) / frameHeight
			}));
			const { top, left, transform } = calculatePopoverPosition(absVerticesCanvas, rect);
			popoverPosition = { top, left, transform };

			// Recalcular usando el tamaño real del popover una vez renderizado
			await tick();
			const rect2 = canvas.getBoundingClientRect();
			const measured = calculatePopoverPosition(
				absVerticesCanvas,
				rect2,
				popoverEl?.offsetWidth ?? undefined,
				popoverEl?.offsetHeight ?? undefined
			);
			popoverPosition = measured;

			// Enfocar el campo de texto al mostrar el popover
			viaInputEl?.focus();
			viaInputEl?.select();
		}
		requestAnimationFrame(redrawCanvas);
	}

	async function handleKeyDown(event: KeyboardEvent) {
		if (pendingPolygon) {
			if (event.key === 'Enter') {
				if (pendingPolygon.via && pendingPolygon.via.trim().length > 0) {
					confirmPendingPolygon();
				}
			}
			if (event.key === 'Escape') cancelPendingPolygon();
			return;
		}

		// Modo zona excluida: Enter confirma si hay al menos 3 puntos
		if (modoZonaExcluida) {
			if (event.key === 'Enter') {
				if (currentPoints.length >= 3) {
					// Ordenar los vértices y agregar como vía con sentido 'Excluida'
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
					await tick(); // forzar actualización inmediata si hay elementos dependientes
				}
			}
			if (event.key === 'Escape') {
				currentPoints = [];
			}
			if (event.key === 'Backspace') currentPoints.pop();
			requestAnimationFrame(redrawCanvas);
			return;
		}
		if (event.key === 'Escape') currentPoints = [];
		if (event.key === 'Backspace') currentPoints.pop();
		requestAnimationFrame(redrawCanvas);
	}

	function confirmPendingPolygon() {
		if (!pendingPolygon) return;
		// Guardar el último sentido elegido para usarlo por defecto en el próximo polígono
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
		requestAnimationFrame(redrawCanvas);
	}

	// --- NUEVA FUNCIÓN ---
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

		// Construir el objeto de envío con las claves correctas para el backend
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

		console.log('Enviando datos:', payload);

		try {
			const response = await apiFetch(`/task/${taskId}/config`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			if (!response.ok) throw new Error('Error en el servidor');
			const result = await response.json();
			console.log('Respuesta del servidor:', result);
			await showAlert({ message: 'Vías guardadas correctamente.', variant: 'success' });
			goto('/');
			// Opcional: limpiar polígonos, redirigir, mostrar mensaje de éxito, etc.
			// poligonos = [];
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

		// Dibujar polígonos confirmados: primero vías normales, luego excluidas para que queden por encima
		poligonos
			.filter((p) => p.sentido !== 'Excluida')
			.forEach((poly) => drawPolygonRel(poly, { confirmed: true }));
		poligonos
			.filter((p) => p.sentido === 'Excluida')
			.forEach((poly) => drawPolygonRel(poly, { confirmed: true }));
		// Dibujar polígono pendiente
		if (pendingPolygon) {
			drawPolygonRel(pendingPolygon, { pending: true });
		}
		// Dibujar puntos actuales
		if (currentPoints.length > 0) {
			ctx.beginPath();
			// Convertir a absolutas usando frame original y escalar a canvas
			const absPoints = currentPoints.map((p) => ({
				x: (p.x * frameWidth * canvas.width) / frameWidth,
				y: (p.y * frameHeight * canvas.height) / frameHeight
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

		// Zonas excluidas ya se dibujan en el paso anterior con estilo especial
	}

	// Reposiciona el popover según el tamaño actual del canvas y del popover
	function updatePopoverPositionForCurrentPending() {
		if (!pendingPolygon || !canvas) return;
		const rect = canvas.getBoundingClientRect();
		// Convertir vértices relativos a px del canvas
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

	// Dibuja polígonos usando coordenadas relativas
	function drawPolygonRel(
		poly: { via: string; sentido: string; vertices: Array<{ x: number; y: number }> },
		options: { confirmed?: boolean; pending?: boolean }
	) {
		// Convertir vértices relativos a absolutos usando frame original y escalar a canvas
		const absVertices = poly.vertices.map((v) => ({
			x: (v.x * frameWidth * canvas.width) / frameWidth,
			y: (v.y * frameHeight * canvas.height) / frameHeight
		}));
		const isExcluded = poly.sentido === 'Excluida';
		const color = isExcluded
			? 'rgba(0,0,0,1)'
			: poly.sentido === 'Entrada'
				? 'rgba(74, 222, 128, 1)'
				: 'rgba(248, 113, 113, 1)';
		ctx.fillStyle = isExcluded
			? 'rgba(0,0,0,1)'
			: color.replace(', 1)', options.pending ? ', 0.5)' : ', 0.3)');
		ctx.beginPath();
		ctx.moveTo(absVertices[0].x, absVertices[0].y);
		for (const v of absVertices.slice(1)) ctx.lineTo(v.x, v.y);
		ctx.closePath();
		ctx.fill();
		ctx.strokeStyle = isExcluded ? 'rgba(0,0,0,1)' : color;
		ctx.lineWidth = options.pending ? 4 : 2;
		if (options.pending) {
			ctx.setLineDash([8, 4]);
		}
		ctx.stroke();
		ctx.setLineDash([]);
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
			ctx.fillText(`${poly.via}`, centro.x, centro.y);
			ctx.shadowBlur = 0;
		}
	}

	function drawExcludedRel(vertices: Array<{ x: number; y: number }>) {
		const absVertices = vertices.map((v) => ({
			x: (v.x * frameWidth * canvas.width) / frameWidth,
			y: (v.y * frameHeight * canvas.height) / frameHeight
		}));
		ctx.save();
		ctx.fillStyle = 'rgba(0,0,0,1)';
		ctx.beginPath();
		ctx.moveTo(absVertices[0].x, absVertices[0].y);
		for (const v of absVertices.slice(1)) ctx.lineTo(v.x, v.y);
		ctx.closePath();
		ctx.fill();
		ctx.restore();
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
							{#if !modoZonaExcluida}
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
						{#if !modoZonaExcluida}
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
				<div class="flex items-center gap-2">
					<!-- Toggle de modos: Entradas/Salidas vs Zonas Excluídas -->
					<div class="mode-toggle" role="group" aria-label="Modo de dibujo">
						<div
							class={`mode-indicator ${modoZonaExcluida ? 'right bg-excluded' : 'left bg-inout'}`}
							aria-hidden="true"
						></div>
						<button
							class="mode-option left"
							disabled={!modoZonaExcluida}
							aria-pressed={!modoZonaExcluida}
							onclick={() => setModoZonaExcluida(false)}
							title="Dibujar entradas/salidas"
						>
							<span class="swap-container">
								<span class="swap-measure">
									{#if !modoZonaExcluida}
										Dibujando entradas/salidas...
									{:else}
										Dibujar entradas/salidas
									{/if}
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
							disabled={modoZonaExcluida}
							aria-pressed={modoZonaExcluida}
							onclick={() => setModoZonaExcluida(true)}
							title="Dibujar zonas excluídas (confirme con Enter)"
						>
							<span class="swap-container">
								<span class="swap-measure">
									{#if modoZonaExcluida}
										Dibujando zonas excluídas...
									{:else}
										Dibujar zonas excluídas
									{/if}
								</span>
								{#if modoZonaExcluida}
									<span class="swap-layer" transition:fade={{ duration: 210 }}
										>Dibujando zonas excluídas...</span
									>
								{:else}
									<span class="swap-layer" transition:fade={{ duration: 210 }}
										>Dibujar zonas excluídas</span
									>
								{/if}
							</span>
						</button>
					</div>
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
			class="lg:grid lg:grid-cols-[320px_1fr] lg:gap-6 items-start flex-1 min-h-0 h-full overflow-hidden"
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
									class="glass-surface p-3 rounded-lg flex justify-between items-center transition-all border"
									class:border-green-400={poly.sentido === 'Entrada'}
									class:border-red-400={poly.sentido === 'Salida'}
									out:fly={{ y: -10, opacity: 0, duration: 250, easing: quintOut }}
								>
									<div>
										<p class="font-semibold text-base">{poly.via}</p>
										<p
											class="text-sm"
											class:text-green-300={poly.sentido === 'Entrada'}
											class:text-red-300={poly.sentido === 'Salida'}
										>
											{poly.sentido}
										</p>
									</div>
									<button
										onclick={() => eliminarPoligono(poly.id)}
										class="glass-button btn-danger"
										aria-label="Eliminar vía"
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											width="20"
											height="20"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="2"
											stroke-linecap="round"
											stroke-linejoin="round"
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
						onclick={handleCanvasClick}
						role="button"
						tabindex="0"
						onkeydown={() => {}}
						aria-label={modoZonaExcluida
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
		/* Altura disponible: viewport menos header + gaps superiores/inferiores del layout */
		height: calc(
			100vh - var(--layout-gap, 0px) - var(--header-height, 0px) - var(--layout-gap, 0px) -
				var(--layout-bottom-gap, 0px) - var(--layout-bottom-gap, 0px) - var(--layout-gap, 0px)
		);
		min-height: calc(
			100vh - var(--layout-gap, 0px) - var(--header-height, 0px) - var(--layout-gap, 0px) -
				var(--layout-bottom-gap, 0px) - var(--layout-bottom-gap, 0px) - var(--layout-gap, 0px)
		);
	}
	.canvas-container {
		position: relative;
		width: 100%;
		cursor: crosshair;
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

	/* Clases de utilidad para reducir duplicación en el HTML */
	.key-kbd {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 600;
		color: #1f2937;
		background-color: #f3f4f6;
		border: 1px solid #e5e7eb;
		border-radius: 0.5rem;
	}

	/* Utilidades para crossfade en el mismo lugar sin afectar layout */
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

	/* Efecto flow/glow del botón Excluir zona cuando está activo */
	/* Toggle de modos */
	.mode-toggle {
		position: relative;
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0;
		align-items: center;
		/* Fondo totalmente transparente para que el lado inactivo se vea "vacío" */
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
	/* Fondos activos */
	.bg-inout {
		/* Gradiente con efecto glass */
		background: linear-gradient(
			90deg,
			rgba(74, 222, 128, 0.35) 0%,
			rgba(74, 222, 128, 0.35) 40%,
			rgba(248, 113, 113, 0.35) 60%,
			rgba(248, 113, 113, 0.35) 100%
		);
		backdrop-filter: blur(8px) saturate(140%);
		-webkit-backdrop-filter: blur(8px) saturate(140%);
		/* Quitar borde/blanco del botón de entradas/salidas */
		border-color: transparent;
		box-shadow: 0 10px 28px rgba(0, 0, 0, 0.4);
	}
	.bg-excluded {
		background: rgba(0, 0, 0, 0.9);
	}

	/* Responsive: reducir ancho mínimo en pantallas chicas */
	@media (max-width: 640px) {
		.mode-toggle {
			min-width: 300px;
			font-size: 0.85rem;
		}
	}
</style>

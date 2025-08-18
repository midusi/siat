<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { quintOut } from 'svelte/easing';
	import { fly } from 'svelte/transition';
	import { page } from '$app/stores';
	import { BACKEND_URL } from '$lib/constants';
	import { apiFetch } from '$lib/api';
	import { goto } from '$app/navigation';
	import { showAlert } from '$lib/dialog';
	import Spinner from '$lib/components/Spinner.svelte';
	import GlassSelect from '$lib/components/GlassSelect.svelte';

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

	// --- Estado del Popover Contextual ---
	let pendingPolygon: {
		via: string;
		sentido: string;
		vertices: Array<{ x: number; y: number }>;
	} | null = null;
	let popoverPosition = { top: 0, left: 0, transform: 'translate(-50%, 15px)' };

	// --- Estado de la Interfaz ---
	let isSubmitting = false; // Para deshabilitar el botón "Finalizar" durante el envío

	// --- Opciones ---
	// Via ahora es texto libre; mantener únicamente los sentidos predefinidos
	let opcionesSentido = ['Entrada', 'Salida'];

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
		window.addEventListener('resize', setupCanvas);

		onDestroy(() => {
			unsubscribePage(); // Limpiar la suscripción
			window.removeEventListener('keydown', handleKeyDown);
			window.removeEventListener('resize', setupCanvas);
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
		if (points.length !== 4) return points;
		const centro = points.reduce((acc, p) => ({ x: acc.x + p.x, y: acc.y + p.y }), { x: 0, y: 0 });
		centro.x /= 4;
		centro.y /= 4;
		return points
			.map((point) => ({
				...point,
				angle: Math.atan2(point.y - centro.y, point.x - centro.x)
			}))
			.sort((a, b) => a.angle - b.angle)
			.map(({ x, y }) => ({ x, y }));
	}

	function calculatePopoverPosition(
		polyVertices: Array<{ x: number; y: number }>,
		canvasRect: DOMRect
	) {
		const centro = polyVertices.reduce((acc, v) => ({ x: acc.x + v.x, y: acc.y + v.y }), {
			x: 0,
			y: 0
		});
		centro.x /= 4;
		centro.y /= 4;
		const popoverHeight = 230;
		const popoverOffsetY = 15;
		let top = centro.y + canvasRect.top + popoverOffsetY;
		let transform = 'translate(-50%, 0)';
		if (top + popoverHeight > window.innerHeight) {
			top = centro.y + canvasRect.top - popoverOffsetY;
			transform = 'translate(-50%, -100%)';
		}
		const popoverWidth = 288; // w-72 = 18rem = 288px
		let left = centro.x + canvasRect.left;
		if (left + popoverWidth / 2 > window.innerWidth) {
			left = window.innerWidth - popoverWidth / 2 - 16; // 16px margin from edge
		}
		if (left - popoverWidth / 2 < 0) {
			left = popoverWidth / 2 + 16; // 16px margin from edge
		}
		return {
			top,
			left,
			transform
		};
	}

	function handleCanvasClick(event: MouseEvent) {
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

		if (currentPoints.length === 4) {
			const verticesOrdenados = ordenarVertices(currentPoints);
			pendingPolygon = {
				vertices: verticesOrdenados,
				via: '',
				sentido: opcionesSentido[0]
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
		}
		requestAnimationFrame(redrawCanvas);
	}

	function handleKeyDown(event: KeyboardEvent) {
		if (pendingPolygon) {
			if (event.key === 'Enter') {
				if (pendingPolygon.via && pendingPolygon.via.trim().length > 0) {
					confirmPendingPolygon();
				}
			}
			if (event.key === 'Escape') cancelPendingPolygon();
			return;
		}
		if (event.key === 'Escape') currentPoints = [];
		if (event.key === 'Backspace') currentPoints.pop();
		requestAnimationFrame(redrawCanvas);
	}

	function confirmPendingPolygon() {
		if (!pendingPolygon) return;
		poligonos = [
			...poligonos,
			{
				id: Date.now(),
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
		if (poligonos.length === 0 || isSubmitting) return;
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
				.map((p) => ({ name: p.via.trim(), polygon: p.vertices.map(toAbs) }))
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
		// Dibujar polígonos confirmados
		poligonos.forEach((poly) => drawPolygonRel(poly, { confirmed: true }));
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
			ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
			ctx.lineWidth = 2;
			ctx.setLineDash([6, 6]);
			ctx.stroke();
			ctx.setLineDash([]);
			absPoints.forEach((p) => {
				ctx.fillStyle = 'rgba(255, 255, 255, 1)';
				ctx.beginPath();
				ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
				ctx.fill();
			});
		}
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
		const color = poly.sentido === 'Entrada' ? 'rgba(74, 222, 128, 1)' : 'rgba(248, 113, 113, 1)';
		ctx.fillStyle = color.replace(', 1)', options.pending ? ', 0.5)' : ', 0.3)');
		ctx.beginPath();
		ctx.moveTo(absVertices[0].x, absVertices[0].y);
		for (const v of absVertices.slice(1)) ctx.lineTo(v.x, v.y);
		ctx.closePath();
		ctx.fill();
		ctx.strokeStyle = color;
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
			centro.x /= 4;
			centro.y /= 4;
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

	$: if (pendingPolygon) requestAnimationFrame(redrawCanvas);
	function goBack() {
		goto('/');
	}
</script>

<div class="page-container">
	<div class="mx-auto">
		<!-- Título y descripción generales -->
		<div class="mb-6 flex items-center justify-between">
			<div>
				<h1 class="heading-1">Asignar Vías</h1>
				<p class="text-white/70 mt-1 text-sm">
					Haz clic 4 veces en la imagen para definir una zona. Usa <kbd class="key-kbd"
						>Backspace</kbd
					>
					para deshacer o
					<kbd class="key-kbd">Esc</kbd> para cancelar.
				</p>
			</div>
			<button
				class="glass-button px-3 py-2 border-white/20 bg-white/10 hover:bg-white/20"
				onclick={goBack}
				aria-label="Volver"
			>
				← Volver
			</button>
		</div>

		<!-- Contenedor Principal con Layout de Grid: sidebar fijo + imagen máxima -->
		<div class="lg:grid lg:grid-cols-[320px_1fr] lg:gap-6 items-start">
			<!-- Columna Izquierda: Lista de Vías y Botón de Finalizar -->
			<div class="flex flex-col h-full glass-card p-4 lg:mr-4 mb-8 lg:mb-0">
				<div>
					<h2 class="heading-2 mb-4">Vías Definidas ({poligonos.length})</h2>
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
				</div>
				<!-- Botón Finalizar -->
				<div class="mt-auto pt-8">
					<button
						onclick={finalizarProceso}
						disabled={poligonos.length === 0 || isSubmitting}
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
			<div class="mt-8 lg:mt-0 w-full">
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
						aria-label="Definir zona en la imagen"
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
</style>

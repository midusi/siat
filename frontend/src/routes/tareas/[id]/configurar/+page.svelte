<script lang="ts">
	import './configurar.css';
	import { buildConfigPayload, centroid, toCanvasPx } from './geometry';
	import { calculatePopoverPosition } from './popover';
	import { createPolygonEditor, OPCIONES_SENTIDO } from './editor.svelte';
	import { defaultColorForSentido } from '$lib/polygon-utils';
	import { errorMessage as apiErrorMessage } from '$lib/services/errors';
	import { fade, fly } from 'svelte/transition';
	import { fetchFirstFrame, saveTaskConfig } from '$lib/services/tasks';
	import GlassSelect from '$lib/components/GlassSelect.svelte';
	import { goto } from '$app/navigation';
	import { onMount, tick } from 'svelte';
	import { page } from '$app/state';
	import { quintOut } from 'svelte/easing';
	import { redraw } from './draw';
	import ScrollArea from '$lib/components/ScrollArea.svelte';
	import { showAlert } from '$lib/dialog.svelte';
	import Spinner from '$lib/components/Spinner.svelte';

	import type { Coordinates, Sentido } from './geometry';
	import type { FirstFrameInfo } from '$lib/types/task';
	import type { PolygonEditor } from './editor.svelte';
	import type { PopoverPosition } from './popover';

	const HANDLE_HIT_RADIUS_PX: number = 15;

	const editor: PolygonEditor = createPolygonEditor();

	let canvas: HTMLCanvasElement | null = $state(null);
	let ctx: CanvasRenderingContext2D | null = $state.raw(null);
	let editingId: number | null = $state(null);
	let editValue: string = $state('');
	let errorMessage: string | null = $state(null);
	let frameHeight: number = $state(1080);
	let frameWidth: number = $state(1920);
	let imageRef: HTMLImageElement | null = $state(null);
	let imageSrc: string = $state('');
	let isLoading: boolean = $state(true);
	let isSubmitting: boolean = $state(false);
	let popoverEl: HTMLDivElement | null = $state(null);
	let popoverPosition: PopoverPosition = $state({
		top: 0,
		left: 0,
		transform: 'translate(-50%, 15px)'
	});
	let viaInputEl: HTMLInputElement | null = $state(null);

	const canSubmit: boolean = $derived(
		editor.entradasCount > 0 && editor.salidasCount > 0 && !isSubmitting
	);
	const taskId: number = $derived(Number(page.params.id));

	$effect(() => {
		redrawCanvas();
	});

	onMount(() => {
		loadFirstFrame();
	});

	const loadFirstFrame = async (): Promise<void> => {
		if (!taskId) {
			return;
		}
		try {
			isLoading = true;
			errorMessage = null;
			const info: FirstFrameInfo = await fetchFirstFrame(taskId);
			frameWidth = info.width;
			frameHeight = info.height;
			imageSrc = `data:image/jpeg;base64,${info.image_b64}`;
		} catch (error) {
			console.error('No se pudo cargar el frame de la tarea:', error);
			errorMessage = apiErrorMessage(
				error,
				'No se pudo cargar la imagen. Por favor, recargue la página.'
			);
		} finally {
			isLoading = false;
		}
	};

	const onResize = (): void => {
		setupCanvas();
		updatePopoverPosition();
	};

	const setupCanvas = (): void => {
		if (!canvas || !imageRef?.complete || !imageRef.naturalWidth) {
			return;
		}
		ctx = canvas.getContext('2d');
		canvas.width = imageRef.clientWidth;
		canvas.height = imageRef.clientHeight;
		requestAnimationFrame(redrawCanvas);
	};

	const canvasPoint = (event: MouseEvent, target: HTMLCanvasElement): Coordinates => {
		const rect: DOMRect = target.getBoundingClientRect();
		return {
			x: (event.clientX - rect.left) / target.width,
			y: (event.clientY - rect.top) / target.height
		};
	};

	const handleRadius = (target: HTMLCanvasElement): Coordinates => ({
		x: HANDLE_HIT_RADIUS_PX / target.width,
		y: HANDLE_HIT_RADIUS_PX / target.height
	});

	const handleCanvasClick = async (event: MouseEvent): Promise<void> => {
		if (!canvas || editor.editMode) {
			return;
		}
		const roadCompleted: boolean = editor.addPoint(canvasPoint(event, canvas));
		if (!roadCompleted) {
			return;
		}
		updatePopoverPosition();
		await tick();
		updatePopoverPosition();

		viaInputEl?.focus();
		viaInputEl?.select();
	};

	const handleCanvasMouseDown = (event: MouseEvent): void => {
		if (!canvas || !editor.editMode) {
			return;
		}
		event.preventDefault();
		editor.pointerDown(canvasPoint(event, canvas), handleRadius(canvas));
	};

	const handleWindowMouseMove = (event: MouseEvent): void => {
		if (!canvas) {
			return;
		}
		editor.pointerMove(canvasPoint(event, canvas), handleRadius(canvas));
	};

	const handleKeyDown = (event: KeyboardEvent): void => {
		editor.handleKey(event.key);
	};

	const startRename = async (id: number, via: string): Promise<void> => {
		editValue = via;
		editingId = id;
		await tick();
		const input: HTMLInputElement | null = document.querySelector(`#rename-input-${id}`);
		input?.focus();
		input?.select();
	};

	const commitRename = (id: number): void => {
		editor.renamePolygon(id, editValue);
		editingId = null;
	};

	const cancelRename = (): void => {
		editingId = null;
	};

	const handleRenameKeydown = (event: KeyboardEvent, id: number): void => {
		if (event.key === 'Enter') {
			commitRename(id);
		}
		if (event.key === 'Escape') {
			cancelRename();
		}
	};

	const finalizarProceso = async (): Promise<void> => {
		if (isSubmitting) {
			return;
		}
		if (editor.entradasCount === 0 || editor.salidasCount === 0) {
			await showAlert({
				message: 'Debes configurar al menos una entrada y una salida antes de continuar.',
				variant: 'warning'
			});
			return;
		}
		isSubmitting = true;
		try {
			await saveTaskConfig(
				taskId,
				buildConfigPayload(editor.polygons, { width: frameWidth, height: frameHeight })
			);
			await showAlert({ message: 'Vías guardadas correctamente.', variant: 'success' });
			goto('/');
		} catch (error) {
			console.error('Fallo al enviar los datos:', error);
			await showAlert({
				message: apiErrorMessage(error, 'Hubo un error al guardar las vías. Inténtalo de nuevo.'),
				variant: 'danger'
			});
		} finally {
			isSubmitting = false;
		}
	};

	const redrawCanvas = (): void => {
		if (!ctx) {
			return;
		}
		redraw(ctx, editor);
	};

	const updatePopoverPosition = (): void => {
		if (!editor.pending || !canvas) {
			return;
		}
		const rect: DOMRect = canvas.getBoundingClientRect();
		const center: Coordinates = centroid(toCanvasPx(editor.pending.vertices, canvas));
		popoverPosition = calculatePopoverPosition(
			{ x: center.x + rect.left, y: center.y + rect.top },
			popoverEl ? { width: popoverEl.offsetWidth, height: popoverEl.offsetHeight } : null,
			{ width: window.innerWidth, height: window.innerHeight }
		);
	};

	const goBack = (): void => {
		goto('/');
	};
</script>

<svelte:window
	onkeydown={handleKeyDown}
	onmousemove={handleWindowMouseMove}
	onmouseup={editor.pointerUp}
	onresize={onResize}
/>

<div class="configurar-page page-container page-vertical">
	<div class="mx-auto flex flex-col flex-1 min-h-0 h-full">
		<div class="mb-2">
			<h1 class="heading-1">Asignar Vías</h1>
			<div class="mt-2 flex items-center justify-between gap-4 flex-wrap">
				<p class="text-white/70 text-sm m-0">
					<span class="swap-container">
						<span class="swap-measure">
							{#if editor.editMode}
								Clic en una zona para seleccionarla. Arrastre para moverla. Arrastre un vértice
								(círculo blanco) para redimensionarla. <kbd class="key-kbd">Esc</kbd> para deseleccionar.
							{:else if !editor.excludedMode}
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
						{#if editor.editMode}
							<span class="swap-layer" transition:fade={{ duration: 210 }}>
								Clic en una zona para seleccionarla. Arrastre para moverla. Arrastre un vértice
								(círculo blanco) para redimensionarla. <kbd class="key-kbd">Esc</kbd> para deseleccionar.
							</span>
						{:else if !editor.excludedMode}
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
					<div
						class="mode-toggle"
						role="group"
						aria-label="Modo de dibujo"
						class:opacity-50={editor.editMode}
						class:pointer-events-none={editor.editMode}
					>
						<div
							class={`mode-indicator ${editor.excludedMode ? 'right bg-excluded' : 'left bg-inout'}`}
							aria-hidden="true"
						></div>
						<button
							class="mode-option left"
							disabled={!editor.excludedMode || editor.editMode}
							aria-pressed={!editor.excludedMode}
							onclick={() => editor.setExcludedMode(false)}
							title="Dibujar entradas/salidas"
						>
							<span class="swap-container">
								<span class="swap-measure">
									{#if !editor.excludedMode}
										Dibujando entradas/salidas...
									{:else}
										Dibujar entradas/salidas
									{/if}
								</span>
								{#if !editor.excludedMode}
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
							disabled={editor.excludedMode || editor.editMode}
							aria-pressed={editor.excludedMode}
							onclick={() => editor.setExcludedMode(true)}
							title="Dibujar zonas excluidas (confirme con Enter)"
						>
							<span class="swap-container">
								<span class="swap-measure">
									{#if editor.excludedMode}
										Dibujando zonas excluidas...
									{:else}
										Dibujar zonas excluidas
									{/if}
								</span>
								{#if editor.excludedMode}
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
					<button
						class="glass-button px-3 py-2 flex items-center gap-1.5 border-white/20"
						class:bg-blue-500={editor.editMode}
						class:bg-opacity-30={editor.editMode}
						class:border-blue-400={editor.editMode}
						class:border-opacity-60={editor.editMode}
						class:bg-white-10={!editor.editMode}
						class:hover-bg-white-20={!editor.editMode}
						onclick={() => editor.setEditMode(!editor.editMode)}
						title={editor.editMode
							? 'Salir del modo edición'
							: 'Mover y redimensionar zonas existentes'}
						aria-pressed={editor.editMode}
					>
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
						{editor.editMode ? 'Editando...' : 'Mover/Redimensionar'}
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

		<div
			class="lg:grid lg:grid-cols-[320px_1fr] lg:gap-6 items-start flex-1 min-h-0 overflow-y-auto"
		>
			<div
				class="flex flex-col h-full max-h-full min-h-0 overflow-hidden glass-card p-4 lg:mr-4 mb-8 lg:mb-0"
			>
				<div class="flex items-center justify-between mb-4 gap-2">
					<h2 class="heading-2">Vías Definidas ({editor.polygons.length})</h2>
				</div>
				<ScrollArea orientation="y" className="flex-1 min-h-0 pr-1" autoHide>
					{#if editor.polygons.length === 0}
						<p class="text-white/70 text-center py-4 glass-surface rounded-lg">
							No hay vías definidas.
						</p>
					{:else}
						<div class="space-y-3">
							{#each editor.polygons as poly (poly.id)}
								{@const color = poly.color ?? defaultColorForSentido(poly.sentido)}
								<div
									class="glass-surface p-3 rounded-lg transition-all border"
									class:border-green-400={poly.sentido === 'Entrada'}
									class:border-red-400={poly.sentido === 'Salida'}
									class:border-white-30={poly.sentido === 'Excluida'}
									class:ring-2={poly.id === editor.selectedId}
									class:ring-white={poly.id === editor.selectedId}
									class:ring-opacity-50={poly.id === editor.selectedId}
									out:fly={{ y: -10, opacity: 0, duration: 250, easing: quintOut }}
								>
									<div class="flex items-center gap-2">
										<label
											class="cursor-pointer flex-shrink-0"
											title="Cambiar color de la zona"
											aria-label="Cambiar color"
										>
											<div
												class="w-5 h-5 rounded-full border border-white/40 flex-shrink-0"
												style="background-color: {color};"
											></div>
											<input
												type="color"
												class="sr-only"
												value={color}
												oninput={(e) => editor.setPolygonColor(poly.id, e.currentTarget.value)}
											/>
										</label>
										<div class="flex-1 min-w-0">
											{#if editingId === poly.id}
												<input
													id="rename-input-{poly.id}"
													class="glass-input text-sm py-0.5 px-2 w-full"
													bind:value={editValue}
													onblur={() => commitRename(poly.id)}
													onkeydown={(e) => handleRenameKeydown(e, poly.id)}
												/>
											{:else}
												<p class="font-semibold text-base truncate" title={poly.via}>{poly.via}</p>
											{/if}
										</div>
										<div class="flex items-center gap-1 flex-shrink-0">
											<button
												onclick={() => startRename(poly.id, poly.via)}
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
											<button
												onclick={() => editor.duplicatePolygon(poly.id)}
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
											<button
												onclick={() => editor.removePolygon(poly.id)}
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
						style="cursor: {editor.cursor};"
						onclick={handleCanvasClick}
						onmousedown={handleCanvasMouseDown}
						role="button"
						tabindex="0"
						onkeydown={() => {}}
						aria-label={editor.editMode
							? 'Seleccionar y editar zona en la imagen'
							: editor.excludedMode
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

	{#if editor.pending}
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
						bind:value={editor.pending.via}
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
						items={OPCIONES_SENTIDO.map((s) => ({ value: s, label: s }))}
						value={editor.pending.sentido}
						onChange={(v) => (editor.pending!.sentido = String(v) as Sentido)}
					/>
				</div>
			</div>
			<div class="flex gap-2 pt-4">
				<button onclick={editor.cancelPending} class="glass-button">Cancelar (Esc)</button>
				<button
					onclick={editor.confirmPending}
					class="glass-button btn-success"
					disabled={!editor.canConfirm}>Confirmar (Enter)</button
				>
			</div>
		</div>
	{/if}
</div>

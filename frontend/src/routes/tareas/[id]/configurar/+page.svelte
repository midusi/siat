<script lang="ts">
	import './configurar.css';
	import { buildConfigPayload, centroid, toCanvasPx } from './geometry';
	import { calculatePopoverPosition } from './popover';
	import { createPolygonEditor, OPCIONES_SENTIDO } from './editor.svelte';
	import { errorMessage as apiErrorMessage } from '$lib/services/errors';
	import { fade, fly } from 'svelte/transition';
	import { fetchFirstFrame, saveTaskConfig } from '$lib/services/tasks';
	import GlassSelect from '$lib/components/GlassSelect.svelte';
	import { goto } from '$app/navigation';
	import Icon from '$lib/components/Icon.svelte';
	import { onMount, tick } from 'svelte';
	import { page } from '$app/state';
	import { polygonColor, redraw } from './draw';
	import { quintOut } from 'svelte/easing';
	import ScrollArea from '$lib/components/ScrollArea.svelte';
	import { showAlert } from '$lib/dialog.svelte';
	import Spinner from '$lib/components/Spinner.svelte';

	import type { Coordinates, Sentido } from './geometry';
	import type { FirstFrameInfo } from '$lib/types/task';
	import type { PolygonEditor } from './editor.svelte';
	import type { PopoverPosition } from './popover';
	import type { SelectItem } from '$lib/types/select';
	import type { Snippet } from 'svelte';

	type HintMode = 'edit' | 'excluded' | 'road';
	type SentidoStyle = { border: string; text: string };

	const HANDLE_HIT_RADIUS_PX: number = 15;
	const SENTIDO_ITEMS: Array<SelectItem<Sentido>> = OPCIONES_SENTIDO.map(
		(sentido: Sentido): SelectItem<Sentido> => ({ value: sentido, label: sentido })
	);
	const SENTIDO_STYLES: Record<Sentido, SentidoStyle> = {
		Entrada: { border: 'border-green-400', text: 'text-green-300' },
		Excluida: { border: 'border-white/30', text: 'text-white/60' },
		Salida: { border: 'border-red-400', text: 'text-red-300' }
	};

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
	const hintMode: HintMode = $derived(
		editor.editMode ? 'edit' : editor.excludedMode ? 'excluded' : 'road'
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
</script>

{#snippet editHint()}
	Clic en una zona para seleccionarla. Arrastre para moverla. Arrastre un vértice (círculo blanco)
	para redimensionarla. <kbd class="key-kbd">Esc</kbd> para deseleccionar.
{/snippet}

{#snippet roadHint()}
	Haga clic 4 veces en la imagen para definir una vía de entrada/salida. Use
	<kbd class="key-kbd">Backspace</kbd> para deshacer o <kbd class="key-kbd">Esc</kbd> para cancelar.
{/snippet}

{#snippet excludedHint()}
	Haga clic para agregar vértices y presione <kbd class="key-kbd">Enter</kbd> para confirmar una
	zona excluída (mín. 3 puntos). Use <kbd class="key-kbd">Backspace</kbd> para deshacer o
	<kbd class="key-kbd">Esc</kbd> para cancelar.
{/snippet}

{#snippet swapHint(mode: HintMode, content: Snippet)}
	<span class="swap-container">
		<span class="swap-measure">{@render content()}</span>
		{#key mode}
			<span class="swap-layer" transition:fade={{ duration: 210 }}>{@render content()}</span>
		{/key}
	</span>
{/snippet}

{#snippet swapLabel(text: string)}
	<span class="swap-container">
		<span class="swap-measure">{text}</span>
		{#key text}
			<span class="swap-layer" transition:fade={{ duration: 210 }}>{text}</span>
		{/key}
	</span>
{/snippet}

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
					{@render swapHint(
						hintMode,
						hintMode === 'edit' ? editHint : hintMode === 'excluded' ? excludedHint : roadHint
					)}
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
							class={[
								'mode-indicator',
								editor.excludedMode ? 'right bg-excluded' : 'left bg-inout'
							]}
							aria-hidden="true"
						></div>
						<button
							class="mode-option left"
							disabled={!editor.excludedMode || editor.editMode}
							aria-pressed={!editor.excludedMode}
							onclick={() => editor.setExcludedMode(false)}
							title="Dibujar entradas/salidas"
						>
							{@render swapLabel(
								editor.excludedMode ? 'Dibujar entradas/salidas' : 'Dibujando entradas/salidas...'
							)}
						</button>
						<button
							class="mode-option right"
							disabled={editor.excludedMode || editor.editMode}
							aria-pressed={editor.excludedMode}
							onclick={() => editor.setExcludedMode(true)}
							title="Dibujar zonas excluidas (confirme con Enter)"
						>
							{@render swapLabel(
								editor.excludedMode ? 'Dibujando zonas excluidas...' : 'Dibujar zonas excluidas'
							)}
						</button>
					</div>
					<button
						class={[
							'glass-button px-3 py-2 flex items-center gap-1.5',
							editor.editMode
								? 'bg-blue-500/30 border-blue-400/60'
								: 'border-white/20 bg-white/10 hover:bg-white/20'
						]}
						onclick={() => editor.setEditMode(!editor.editMode)}
						title={editor.editMode
							? 'Salir del modo edición'
							: 'Mover y redimensionar zonas existentes'}
						aria-pressed={editor.editMode}
					>
						<Icon name="move" class="h-[15px] w-[15px]" />
						{editor.editMode ? 'Editando...' : 'Mover/Redimensionar'}
					</button>
					<a
						href="/"
						class="glass-button px-3 py-2 flex items-center gap-1.5 border-white/20 bg-white/10 hover:bg-white/20"
					>
						<Icon name="arrow-left" class="h-4 w-4" />
						Volver
					</a>
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
				<ScrollArea class="flex-1 min-h-0 pr-1" autoHide>
					{#if editor.polygons.length === 0}
						<p class="text-white/70 text-center py-4 glass-surface rounded-lg">
							No hay vías definidas.
						</p>
					{:else}
						<div class="space-y-3">
							{#each editor.polygons as poly (poly.id)}
								{@const color = polygonColor(poly)}
								<div
									class={[
										'glass-surface p-3 rounded-lg transition-all border',
										SENTIDO_STYLES[poly.sentido].border,
										poly.id === editor.selectedId && 'ring-2 ring-white/50'
									]}
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
												<Icon name="edit" class="h-3.5 w-3.5" />
											</button>
											<button
												onclick={() => editor.duplicatePolygon(poly.id)}
												class="glass-button p-1.5"
												title="Duplicar zona"
												aria-label="Duplicar vía"
											>
												<Icon name="copy" class="h-3.5 w-3.5" />
											</button>
											<button
												onclick={() => editor.removePolygon(poly.id)}
												class="glass-button btn-danger p-1.5"
												aria-label="Eliminar vía"
											>
												<Icon name="trash" class="h-3.5 w-3.5" />
											</button>
										</div>
									</div>
									<p class={['text-sm mt-1 ml-7', SENTIDO_STYLES[poly.sentido].text]}>
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
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<div
						class="canvas-container glass-card overflow-hidden shadow-2xl"
						style="cursor: {editor.cursor};"
						onclick={handleCanvasClick}
						onmousedown={handleCanvasMouseDown}
						role="button"
						tabindex="0"
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
							onload={setupCanvas}
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
						items={SENTIDO_ITEMS}
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

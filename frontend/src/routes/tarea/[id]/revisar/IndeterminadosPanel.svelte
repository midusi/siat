<script lang="ts">
	import GlassSelect from '$lib/components/GlassSelect.svelte';
	import * as review from './review';
	import ScrollArea from '$lib/components/ScrollArea.svelte';
	import SearchInput from '$lib/components/SearchInput.svelte';
	import { showConfirm } from '$lib/dialog';
	import Spinner from '$lib/components/Spinner.svelte';

	type Item = { value: string; label: string };
	type Field = 'class' | 'in' | 'out';

	let {
		items,
		vehicleItems,
		zoneItems,
		savingById,
		mergeInProgress,
		liveIds,
		activeId,
		height,
		classColor,
		onselect,
		onedit,
		onconfirm,
		ondelete,
		onmerge
	}: {
		items: [string, review.Indeterminado][];
		vehicleItems: Item[];
		zoneItems: Item[];
		savingById: Record<string, boolean>;
		mergeInProgress: boolean;
		liveIds: Set<string>;
		activeId: string | null;
		height: number;
		classColor: (cls: string) => string;
		onselect: (trackId: string) => void;
		onedit: (trackId: string, field: Field, value: string) => void;
		onconfirm: (trackId: string) => void;
		ondelete: (trackId: string) => void;
		onmerge: (keepId: string, removeId: string) => Promise<void>;
	} = $props();

	let mergeModeActive = $state(false);
	let mergeSourceId = $state<string | null>(null);
	let searchInputEl = $state<HTMLInputElement | null>(null);
	let searchQuery = $state('');

	let visibleItems = $derived.by(() => {
		const q = searchQuery.trim();
		if (!q) {
			return items;
		}
		return items.filter(([id]) => id.includes(q));
	});

	const onGlobalKeyDown = (e: KeyboardEvent) => {
		if (e.ctrlKey && e.key.toLowerCase() === 'k') {
			e.preventDefault();
			searchQuery = '';
			queueMicrotask(() => searchInputEl?.focus());
		}
	};

	const cancelMergeMode = () => {
		mergeModeActive = false;
		mergeSourceId = null;
	};

	const toggleMergeFrom = (trackId: string) => {
		if (!mergeModeActive) {
			if (!mergeInProgress) {
				mergeModeActive = true;
				mergeSourceId = trackId;
			}
			return;
		}
		if (mergeSourceId === trackId) {
			cancelMergeMode();
		}
	};

	const onCardClick = async (trackId: string) => {
		if (!mergeModeActive) {
			onselect(trackId);
			return;
		}
		if (!mergeSourceId) {
			return;
		}
		if (mergeSourceId === trackId) {
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
		if (proceed) {
			await onmerge(keepId, removeId);
		}
		cancelMergeMode();
	};

	const withoutPropagation = (fn: () => void) => (e: Event) => {
		e.stopPropagation();
		fn();
	};
</script>

<svelte:window onkeydown={onGlobalKeyDown} />

{#snippet select(trackId: string, field: Field, options: Item[], value: string, label: string)}
	<GlassSelect
		items={options}
		{value}
		ariaLabel={`${label} para ${trackId}`}
		stopClickPropagation={true}
		disabled={mergeModeActive || mergeInProgress}
		onChange={(val) => onedit(trackId, field, String(val ?? ''))}
	/>
{/snippet}

<div
	class="w-full md:w-[420px] 2xl:w-[460px] shrink-0 glass-card p-1 rounded-lg shadow-lg flex flex-col"
	style:height={height > 0 ? `${height}px` : 'auto'}
>
	<h2 class="text-xl font-semibold mt-3 mb-2 text-center">Vehículos Indeterminados</h2>
	<div class="px-2 mb-3">
		<SearchInput
			bind:ref={searchInputEl}
			bind:value={searchQuery}
			placeholder="Buscar por ID  (Ctrl + K)"
		/>
	</div>

	<ScrollArea orientation="y" className="flex-1">
		<div class="space-y-3 p-1">
			{#each visibleItems as [trackId, item] (trackId)}
				{@const canConfirm =
					!review.isUnknownLabel(item.labels.in) && !review.isUnknownLabel(item.labels.out)}
				{@const saving = !!savingById[trackId]}
				{@const isMergeSource = mergeModeActive && mergeSourceId === trackId}
				{@const isLive = liveIds.has(trackId) || trackId === activeId}
				<!-- Click en toda la tarjeta para el mouse; con teclado se usa el botón del ID -->
				<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
				<div
					id={`ind-card-${trackId}`}
					tabindex="-1"
					class={[
						'p-3 rounded-xl border cursor-pointer outline-none backdrop-blur-[10px] bg-[hsl(var(--background)/0.6)]',
						isLive
							? 'border-white shadow-[0_0_3px_rgba(255,255,255,0.5),0_0_7px_rgba(255,255,255,0.7)]'
							: 'border-[hsl(var(--border))] transition-[border-color,box-shadow] duration-200 ease-in-out hover:border-white/35 hover:shadow-[0_0_8px_rgba(255,255,255,0.2)]'
					]}
					onclick={withoutPropagation(() => onCardClick(trackId))}
				>
					<div class="flex justify-between items-center mb-2">
						<button
							type="button"
							class="font-bold text-lg text-left cursor-pointer"
							onclick={withoutPropagation(() => onCardClick(trackId))}
						>
							ID: {trackId}
						</button>
						<button
							onclick={withoutPropagation(() => ondelete(trackId))}
							class="glass-button btn-danger text-xs py-1 px-2 disabled:opacity-60 disabled:cursor-not-allowed"
							disabled={saving || mergeModeActive || mergeInProgress}
						>
							{#if saving}
								<Spinner size={14} className="inline-block mr-1" />
								Eliminando...
							{:else}
								Eliminar
							{/if}
						</button>
					</div>
					<div class="grid grid-cols-4 gap-2 items-center mb-2 text-sm">
						<span class="text-gray-400">Clase:</span>
						<div class="col-span-3 flex items-center gap-2">
							<span class="color-dot" style:background={classColor(item.class)}></span>
							{@render select(trackId, 'class', vehicleItems, item.class, 'Clase')}
						</div>
					</div>
					<div class="grid grid-cols-4 gap-2 items-center mb-3 text-sm">
						<span class="text-gray-400">Ruta:</span>
						<div class="col-span-3 flex items-center gap-1">
							<div class="w-full">
								{@render select(trackId, 'in', zoneItems, item.labels.in ?? '', 'Entrada')}
							</div>
							<span class="text-gray-400">→</span>
							<div class="w-full">
								{@render select(trackId, 'out', zoneItems, item.labels.out ?? '', 'Salida')}
							</div>
						</div>
						<div class="col-start-2 col-span-3 mt-1">
							<button
								type="button"
								onclick={withoutPropagation(() => toggleMergeFrom(trackId))}
								class={[
									'w-full py-2 text-sm font-semibold rounded-xl border border-white transition-[background-color,color,box-shadow] duration-[180ms] disabled:opacity-60 disabled:cursor-not-allowed',
									isMergeSource
										? 'bg-white text-black shadow-glow'
										: ['bg-transparent text-white', !mergeModeActive && 'hover:bg-white/[0.08]']
								]}
								disabled={(mergeModeActive && !isMergeSource) || saving || mergeInProgress}
							>
								{isMergeSource ? 'Uniendo...' : '+ Unir'}
							</button>
						</div>
					</div>
					<button
						onclick={withoutPropagation(() => onconfirm(trackId))}
						onmousedown={(e) => e.stopPropagation()}
						onmouseup={(e) => e.stopPropagation()}
						disabled={!canConfirm || saving || mergeModeActive || mergeInProgress}
						class="w-full py-2 text-sm font-semibold rounded flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed glass-button"
						class:btn-success={canConfirm}
						class:btn-disabled={!canConfirm}
					>
						{#if saving}
							<Spinner size={16} />
							Guardando...
						{:else}
							Confirmar Ruta
						{/if}
					</button>
				</div>
			{/each}
		</div>
	</ScrollArea>
</div>

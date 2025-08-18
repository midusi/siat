<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { portal } from '$lib/actions/portal';

	type Item = { value: string | number; label: string };

	// Props
	let {
		items = [],
		placeholder = 'Seleccione...',
		disabled = false,
		id,
		name,
		ariaLabel,
		ariaLabelledby,
		value: propValue = null,
		onChange,
		stopClickPropagation = false
	} = $props<{
		items?: Item[];
		placeholder?: string;
		disabled?: boolean;
		id?: string;
		name?: string;
		ariaLabel?: string;
		ariaLabelledby?: string;
		value?: string | number | null;
		onChange?: (val: string | number | null) => void;
		stopClickPropagation?: boolean;
	}>();
	let value = $state<string | number | null>(propValue);

	let open = $state(false);
	let highlighted = $state<number>(-1);
	let buttonEl = $state<HTMLButtonElement | null>(null);
	let menuEl = $state<HTMLDivElement | null>(null);
	let rect = $state({ top: 0, left: 0, width: 0, height: 0 });

	// keep local value in sync with parent prop
	$effect(() => {
		value = propValue;
	});

	const selectedIndex = $derived(items.findIndex((i: Item) => i.value === value));
	const selectedLabel = $derived(selectedIndex >= 0 ? items[selectedIndex]?.label : '');

	function updatePosition() {
		if (!browser || !buttonEl) return;
		const r = buttonEl.getBoundingClientRect();
		rect = {
			top: Math.round(r.bottom + 4),
			left: Math.round(r.left),
			width: Math.round(r.width),
			height: Math.round(r.height)
		};
	}

	function toggle() {
		if (disabled) return;
		if (!open) {
			updatePosition();
			open = true;
			highlighted = selectedIndex;
		} else {
			open = false;
		}
	}

	function close() {
		open = false;
	}

	function selectIndex(idx: number) {
		const it = items[idx] as Item | undefined;
		if (!it) return;
		value = it.value;
		if (typeof onChange === 'function') onChange(value);
		close();
	}

	function onKeydown(e: KeyboardEvent) {
		if (disabled) return;
		if (!open && (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ')) {
			e.preventDefault();
			toggle();
			return;
		}
		if (!open) return;
		if (e.key === 'Escape') {
			e.preventDefault();
			close();
		} else if (e.key === 'ArrowDown') {
			e.preventDefault();
			highlighted = Math.min(items.length - 1, (highlighted < 0 ? selectedIndex : highlighted) + 1);
			scrollHighlightedIntoView();
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			const start = highlighted < 0 ? (selectedIndex >= 0 ? selectedIndex : 0) : highlighted;
			highlighted = Math.max(0, start - 1);
			scrollHighlightedIntoView();
		} else if (e.key === 'Enter') {
			e.preventDefault();
			if (highlighted >= 0) selectIndex(highlighted);
		} else if (e.key === 'Home') {
			e.preventDefault();
			highlighted = 0;
			scrollHighlightedIntoView();
		} else if (e.key === 'End') {
			e.preventDefault();
			highlighted = items.length - 1;
			scrollHighlightedIntoView();
		}
	}

	function scrollHighlightedIntoView() {
		if (!menuEl) return;
		const el = menuEl.querySelector('[data-highlighted="true"]') as HTMLElement | null;
		if (el) el.scrollIntoView({ block: 'nearest' });
	}

	function onWindow() {
		if (!open) return;
		updatePosition();
	}

	onMount(() => {
		if (!browser) return;
		window.addEventListener('scroll', onWindow, true);
		window.addEventListener('resize', onWindow, true);
		return () => {
			window.removeEventListener('scroll', onWindow, true);
			window.removeEventListener('resize', onWindow, true);
		};
	});
</script>

<!-- Control -->
<button
	class="glass-input flex items-center justify-between gap-2 cursor-pointer select-none"
	bind:this={buttonEl}
	type="button"
	{id}
	{name}
	aria-label={ariaLabel}
	aria-labelledby={ariaLabelledby}
	aria-expanded={open}
	aria-haspopup="listbox"
	{disabled}
	onclick={(e) => {
		if (stopClickPropagation) e.stopPropagation();
		toggle();
	}}
	onkeydown={onKeydown}
>
	<span class={selectedLabel ? 'opacity-100' : 'opacity-70'}>
		{selectedLabel || placeholder}
	</span>
	<!-- Chevron -->
	<svg
		width="16"
		height="16"
		viewBox="0 0 24 24"
		fill="none"
		stroke="currentColor"
		class="opacity-80"
	>
		<path d="M6 9l6 6 6-6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
	</svg>
</button>

{#if open}
	<!-- Click-catcher overlay -->
	<button
		type="button"
		class="fixed inset-0 z-[80]"
		aria-label="Cerrar menú"
		onclick={close}
		onkeydown={(e) => {
			if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') {
				e.preventDefault();
				close();
			}
		}}
	></button>
	<!-- Dropdown menu via portal -->
	<div
		use:portal
		class="z-[200]"
		style={`position: fixed; top: ${rect.top}px; left: ${rect.left}px; width: ${rect.width}px;`}
	>
		<div
			class="glass-strong frost frost-polarized border p-1 shadow-xl overflow-auto max-h-[300px]"
			bind:this={menuEl}
			role="listbox"
		>
			{#if items.length === 0}
				<div class="px-3 py-2 text-sm text-white/70">Sin opciones</div>
			{:else}
				{#each items as it, i}
					<button
						type="button"
						role="option"
						aria-selected={i === selectedIndex}
						data-highlighted={i === highlighted}
						class="flex w-full items-center justify-between px-3 py-2 text-sm rounded
                            {i === selectedIndex
							? 'bg-white/15 text-white'
							: 'text-white/90 hover:bg-white/10'}
                            {i === highlighted ? 'ring-1 ring-white/20' : ''}"
						onclick={() => selectIndex(i)}
						onmousemove={() => (highlighted = i)}
					>
						<span>{it.label}</span>
						{#if i === selectedIndex}
							<svg
								width="16"
								height="16"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								class="opacity-90"
							>
								<path
									d="M20 6L9 17l-5-5"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
								/>
							</svg>
						{/if}
					</button>
				{/each}
			{/if}
		</div>
	</div>
{/if}

<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import { portal } from '$lib/actions/portal';

	import type { SelectItem } from '$lib/types/select';

	type SelectValue = string | number;
	type MenuPosition = { top: number; left: number; width: number };
	type Props = {
		ariaLabel?: string;
		ariaLabelledby?: string;
		disabled?: boolean;
		id?: string;
		items?: Array<SelectItem>;
		name?: string;
		onChange?: (value: SelectValue | null) => void;
		placeholder?: string;
		stopClickPropagation?: boolean;
		value?: SelectValue | null;
	};

	const MENU_OFFSET_PX: number = 4;
	const SEARCHABLE_KEY: RegExp = /[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]/;

	let {
		ariaLabel,
		ariaLabelledby,
		disabled = false,
		id,
		items = [],
		name,
		onChange,
		placeholder = 'Seleccione...',
		stopClickPropagation = false,
		value: propValue = null
	}: Props = $props();

	const menuId: string = $props.id();

	let buttonEl: HTMLButtonElement | null = $state(null);
	let highlighted: number = $state(-1);
	let menuEl: HTMLDivElement | null = $state(null);
	let menuPosition: MenuPosition = $state({ top: 0, left: 0, width: 0 });
	let open: boolean = $state(false);
	let value: SelectValue | null = $derived(propValue);

	const selectedIndex: number = $derived(items.findIndex((item) => item.value === value));
	const selectedLabel: string = $derived(items[selectedIndex]?.label ?? '');

	const optionId = (index: number): string => `${menuId}-option-${index}`;

	const updatePosition = (): void => {
		if (!buttonEl) {
			return;
		}
		const bounds: DOMRect = buttonEl.getBoundingClientRect();
		menuPosition = {
			top: Math.round(bounds.bottom + MENU_OFFSET_PX),
			left: Math.round(bounds.left),
			width: Math.round(bounds.width)
		};
	};

	const openMenu = (): void => {
		updatePosition();
		open = true;
		highlighted = selectedIndex;
	};

	const close = (): void => {
		open = false;
	};

	const toggle = (): void => {
		if (disabled) {
			return;
		}
		if (open) {
			close();
		} else {
			openMenu();
		}
	};

	const scrollHighlightedIntoView = (): void => {
		menuEl?.querySelector('[data-highlighted="true"]')?.scrollIntoView({ block: 'nearest' });
	};

	const setHighlighted = (index: number): void => {
		highlighted = index;
		scrollHighlightedIntoView();
	};

	const selectIndex = (index: number, closeMenu: boolean = true): void => {
		const item: SelectItem | undefined = items[index];
		if (!item) {
			return;
		}
		value = item.value;
		onChange?.(value);
		if (closeMenu) {
			close();
		}
	};

	const normalizeText = (text: string): string =>
		text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLocaleLowerCase('es');

	const highlightFirstMatch = (key: string): void => {
		const normalizedKey: string = normalizeText(key);
		const matches = (item: SelectItem): boolean =>
			normalizeText(item.label).startsWith(normalizedKey);
		const nextMatch: number = items.findIndex(
			(item, index) => index > selectedIndex && matches(item)
		);
		const matchIndex: number = nextMatch >= 0 ? nextMatch : items.findIndex(matches);
		if (matchIndex < 0) {
			return;
		}
		highlighted = matchIndex;
		selectIndex(matchIndex, false);
		requestAnimationFrame(scrollHighlightedIntoView);
	};

	const handleKeydown = (event: KeyboardEvent): void => {
		if (disabled) {
			return;
		}
		if (event.key.length === 1 && SEARCHABLE_KEY.test(event.key)) {
			event.preventDefault();
			if (!open) {
				openMenu();
			}
			highlightFirstMatch(event.key);
			return;
		}
		if (!open) {
			if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
				event.preventDefault();
				openMenu();
			}
			return;
		}
		switch (event.key) {
			case 'Escape':
				event.stopPropagation();
				close();
				break;
			case 'ArrowDown':
				setHighlighted(
					Math.min(items.length - 1, (highlighted < 0 ? selectedIndex : highlighted) + 1)
				);
				break;
			case 'ArrowUp':
				setHighlighted(
					Math.max(0, (highlighted < 0 ? Math.max(selectedIndex, 0) : highlighted) - 1)
				);
				break;
			case 'Enter':
				if (highlighted >= 0) {
					selectIndex(highlighted);
				}
				break;
			case 'Home':
				setHighlighted(0);
				break;
			case 'End':
				setHighlighted(items.length - 1);
				break;
			default:
				return;
		}
		event.preventDefault();
	};

	const handleClick = (event: MouseEvent): void => {
		if (stopClickPropagation) {
			event.stopPropagation();
		}
		toggle();
	};

	const handleViewportChange = (): void => {
		if (open) {
			updatePosition();
		}
	};
</script>

<svelte:window onscrollcapture={handleViewportChange} onresize={handleViewportChange} />

<button
	class="glass-input flex items-center justify-between gap-2 cursor-pointer select-none"
	bind:this={buttonEl}
	type="button"
	{id}
	{name}
	role="combobox"
	aria-label={ariaLabel}
	aria-labelledby={ariaLabelledby}
	aria-expanded={open}
	aria-haspopup="listbox"
	aria-controls={open ? menuId : undefined}
	aria-activedescendant={open && highlighted >= 0 ? optionId(highlighted) : undefined}
	{disabled}
	onclick={handleClick}
	onkeydown={handleKeydown}
>
	<span class={selectedLabel ? 'opacity-100' : 'opacity-70'}>
		{selectedLabel || placeholder}
	</span>
	<Icon name="chevron-down" class="h-4 w-4 opacity-80" />
</button>

{#if open}
	<button
		type="button"
		class="fixed inset-0 z-[80]"
		tabindex="-1"
		aria-label="Cerrar menú"
		onclick={close}
	></button>
	<div
		use:portal
		class="z-[200]"
		style="position: fixed; top: {menuPosition.top}px; left: {menuPosition.left}px; width: {menuPosition.width}px;"
	>
		<div
			id={menuId}
			class="glass-strong frost frost-polarized border p-1 shadow-xl overflow-auto max-h-[300px]"
			bind:this={menuEl}
			role="listbox"
		>
			{#if items.length === 0}
				<div class="px-3 py-2 text-sm text-white/70">Sin opciones</div>
			{:else}
				{#each items as item, index (item.value)}
					<button
						id={optionId(index)}
						type="button"
						role="option"
						tabindex="-1"
						aria-selected={index === selectedIndex}
						data-highlighted={index === highlighted}
						class={[
							'flex w-full items-center justify-between px-3 py-2 text-sm rounded cursor-pointer',
							index === selectedIndex
								? 'bg-white/15 text-white'
								: 'text-white/90 hover:bg-white/10',
							index === highlighted && 'ring-1 ring-white/20'
						]}
						onclick={() => selectIndex(index)}
						onmousemove={() => (highlighted = index)}
					>
						<span>{item.label}</span>
						{#if index === selectedIndex}
							<Icon name="check" class="h-4 w-4 opacity-90" />
						{/if}
					</button>
				{/each}
			{/if}
		</div>
	</div>
{/if}

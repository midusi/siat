<script lang="ts">
	import { cubicOut } from 'svelte/easing';
	import Icon from '$lib/components/Icon.svelte';
	import { scale } from 'svelte/transition';

	import type { Snippet } from 'svelte';

	type Props = {
		children: Snippet;
		closable?: boolean;
		dimmed?: boolean;
		label?: string;
		onclose: () => void;
		open: boolean;
		title?: string;
	};

	let { children, closable = true, dimmed = true, label, onclose, open, title }: Props = $props();

	const titleId: string = $props.id();

	$effect(() => {
		if (!open) {
			return;
		}
		document.body.style.overflow = 'hidden';
		return () => {
			document.body.style.overflow = '';
		};
	});

	const handleWindowKeydown = (event: KeyboardEvent): void => {
		if (open && event.key === 'Escape') {
			onclose();
		}
	};
</script>

<svelte:window onkeydown={handleWindowKeydown} />

{#if open}
	<div class="fixed inset-0 z-[100] flex items-center justify-center">
		<button
			type="button"
			class={['absolute inset-0', dimmed ? 'bg-black/40' : 'bg-transparent']}
			aria-label="Cerrar"
			onclick={onclose}
		></button>
		<div
			class="relative mx-4 w-full max-w-md glass-strong frost frost-polarized border p-6 shadow-2xl"
			role="dialog"
			aria-modal="true"
			aria-labelledby={title ? titleId : undefined}
			aria-label={title ? undefined : label}
			transition:scale={{ duration: 150, easing: cubicOut }}
		>
			{#if closable}
				<button
					type="button"
					class="absolute top-3 right-3 text-white/70 hover:text-white"
					onclick={onclose}
					aria-label="Cerrar"
				>
					<Icon name="close" />
				</button>
			{/if}

			{#if title}
				<h3 id={titleId} class="mb-4 text-lg font-semibold">{title}</h3>
			{/if}

			{@render children()}
		</div>
	</div>
{/if}

<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';

	let {
		open,
		title,
		onclose,
		children
	}: {
		open: boolean;
		title?: string;
		onclose: () => void;
		children: Snippet;
	} = $props();

	const onKeydown = (e: KeyboardEvent): void => {
		if (open && e.key === 'Escape') {
			onclose();
		}
	};
</script>

<svelte:window onkeydown={onKeydown} />

{#if open}
	<div class="fixed inset-0 z-[100] flex items-center justify-center p-4">
		<button type="button" class="absolute inset-0 bg-black/40" aria-label="Cerrar" onclick={onclose}
		></button>
		<div
			class="relative mx-4 w-full max-w-md glass-strong frost frost-polarized border p-6 shadow-2xl"
			role="dialog"
			aria-modal="true"
			aria-label={title}
		>
			<button
				type="button"
				class="absolute top-3 right-3 text-white/70 hover:text-white"
				onclick={onclose}
				aria-label="Cerrar"
			>
				<Icon name="close" />
			</button>

			{#if title}
				<h3 class="text-lg font-semibold mb-4">{title}</h3>
			{/if}

			{@render children()}
		</div>
	</div>
{/if}

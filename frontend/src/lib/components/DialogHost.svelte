<script lang="ts">
	import { cubicOut } from 'svelte/easing';
	import { dialog } from '$lib/dialog.svelte';
	import { scale } from 'svelte/transition';

	import type { Variant } from '$lib/types/variant';

	const VARIANT_CLASSES: Record<Variant, string> = {
		default: 'border-white/20 bg-white/10 hover:bg-white/20 text-white/90',
		danger: 'border-red-600/50 bg-red-600/15 hover:bg-red-600/25 text-red-100',
		success: 'border-green-500/40 bg-green-400/12 hover:bg-green-400/20 text-green-100',
		warning: 'border-amber-400/40 bg-amber-300/12 hover:bg-amber-300/20 text-amber-100',
		info: 'border-sky-400/40 bg-sky-300/12 hover:bg-sky-300/20 text-sky-100'
	};

	$effect(() => {
		document.body.style.overflow = dialog.current ? 'hidden' : '';
		return () => {
			document.body.style.overflow = '';
		};
	});

	const handleWindowKeydown = (event: KeyboardEvent): void => {
		if (event.key === 'Escape') {
			dialog.close(false);
		}
	};
</script>

<svelte:window onkeydown={handleWindowKeydown} />

{#if dialog.current}
	<div class="fixed inset-0 z-[100] flex items-center justify-center">
		<button
			class="absolute inset-0 bg-transparent"
			type="button"
			aria-label="Cerrar diálogo"
			onclick={() => dialog.close(false)}
		></button>
		<div
			class="relative mx-4 w-full max-w-md glass-strong frost frost-polarized border p-5 shadow-2xl"
			transition:scale={{ duration: 150, easing: cubicOut }}
		>
			{#if dialog.current.title}
				<h3 class="mb-3 text-lg font-semibold">{dialog.current.title}</h3>
			{/if}
			<p class="mb-5 opacity-90 whitespace-pre-line">{dialog.current.message}</p>
			<div class="flex justify-end gap-2">
				{#if dialog.current.type === 'confirm'}
					<button class="glass-button px-4 py-2" onclick={() => dialog.close(false)}>
						{dialog.current.cancelText}
					</button>
				{/if}
				<button
					class="glass-button px-4 py-2 {VARIANT_CLASSES[dialog.current.variant]}"
					onclick={() => dialog.close(true)}
				>
					{dialog.current.confirmText}
				</button>
			</div>
		</div>
	</div>
{/if}

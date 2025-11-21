<script lang="ts">
	import { toasts, type Toast } from '$lib/toast';
	import { fly, fade } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';

	let items: Toast[] = [];
	toasts.subscribe((v) => (items = v));

	function colorClasses(variant: Toast['variant']): string {
		switch (variant) {
			case 'success':
				return 'border-green-500/40 bg-green-400/12 text-green-100';
			case 'danger':
				return 'border-red-600/50 bg-red-600/15 text-red-100';
			case 'warning':
				return 'border-amber-400/40 bg-amber-300/12 text-amber-100';
			case 'info':
				return 'border-sky-400/40 bg-sky-300/12 text-sky-100';
			default:
				return 'border-white/20 bg-white/10 text-white/90';
		}
	}

	function getIcon(variant: Toast['variant']) {
		if (variant === 'success') return '✔';
		if (variant === 'danger') return '⛔';
		if (variant === 'warning') return '⚠️';
		if (variant === 'info') return 'ℹ️';
		return '•';
	}

	function autoDismiss(node: HTMLElement, params: { id: number; duration: number }) {
		const timer = setTimeout(() => toasts.dismissToast(params.id), params.duration);
		return {
			destroy() {
				clearTimeout(timer);
			}
		};
	}
</script>

<div class="pointer-events-none fixed inset-0 z-[90] flex items-end justify-end p-4">
	<div class="flex w-full max-w-sm flex-col gap-2">
		{#each items as t (t.id)}
			<div
				use:autoDismiss={{ id: t.id, duration: t.duration }}
				class="pointer-events-auto glass-strong frost frost-polarized border p-3 shadow-xl {colorClasses(
					t.variant
				)}"
				in:fly={{ y: 20, duration: 180, easing: cubicOut }}
				out:fade
			>
				<div class="flex items-start gap-2">
					<div class="mt-0.5 text-sm">{getIcon(t.variant)}</div>
					<div class="flex-1 text-sm leading-5">{t.message}</div>
					<button
						class="ml-2 text-white/80 hover:text-white cursor-pointer"
						on:click={() => toasts.dismissToast(t.id)}
						aria-label="Cerrar">✕</button
					>
				</div>
			</div>
		{/each}
	</div>
</div>

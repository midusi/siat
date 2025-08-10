<script lang="ts">
	import { toasts, type Toast } from '$lib/toast';
	import { fly, fade } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';

	let items: Toast[] = [];
	toasts.subscribe((v) => (items = v));

	function colorClasses(variant: Toast['variant']): string {
		switch (variant) {
			case 'success':
				return 'bg-emerald-700/90 border-emerald-500 text-emerald-50';
			case 'danger':
				return 'bg-red-700/90 border-red-500 text-red-50';
			case 'warning':
				return 'bg-amber-700/90 border-amber-500 text-amber-50';
			case 'info':
				return 'bg-blue-700/90 border-blue-500 text-blue-50';
			default:
				return 'bg-gray-700/90 border-gray-500 text-gray-50';
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
				class="pointer-events-auto rounded border p-3 shadow-xl backdrop-blur-md {colorClasses(
					t.variant
				)}"
				in:fly={{ y: 20, duration: 180, easing: cubicOut }}
				out:fade
			>
				<div class="flex items-start gap-2">
					<div class="mt-0.5 text-sm">{getIcon(t.variant)}</div>
					<div class="flex-1 text-sm leading-5">{t.message}</div>
					<button
						class="ml-2 text-white/80 hover:text-white"
						on:click={() => toasts.dismissToast(t.id)}
						aria-label="Cerrar">✕</button
					>
				</div>
			</div>
		{/each}
	</div>
</div>

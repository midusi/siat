<script lang="ts">
	import { cubicOut } from 'svelte/easing';
	import { fade, fly } from 'svelte/transition';
	import Icon from '$lib/components/Icon.svelte';
	import { toasts } from '$lib/toast.svelte';
	import { VARIANT_CLASSES } from '$lib/variant';

	import type { Action } from 'svelte/action';
	import type { IconName } from '$lib/components/Icon.svelte';
	import type { Variant } from '$lib/types/variant';

	type AutoDismissParams = {
		duration: number;
		id: number;
	};

	const VARIANT_ICONS: Record<Variant, IconName> = {
		default: 'info',
		danger: 'alert-circle',
		success: 'check-circle',
		warning: 'alert-triangle',
		info: 'info'
	};

	const autoDismiss: Action<HTMLDivElement, AutoDismissParams> = (_node, params) => {
		const timer: ReturnType<typeof setTimeout> = setTimeout(
			() => toasts.dismissToast(params.id),
			params.duration
		);
		return { destroy: (): void => clearTimeout(timer) };
	};
</script>

<div class="pointer-events-none fixed inset-0 z-[90] flex items-end justify-end p-4">
	<div class="flex w-full max-w-sm flex-col gap-2">
		{#each toasts.list as t (t.id)}
			<div
				use:autoDismiss={{ id: t.id, duration: t.duration }}
				class={[
					'pointer-events-auto glass-strong frost frost-polarized border p-3 shadow-xl',
					VARIANT_CLASSES[t.variant]
				]}
				in:fly={{ y: 20, duration: 180, easing: cubicOut }}
				out:fade
			>
				<div class="flex items-start gap-2">
					<Icon name={VARIANT_ICONS[t.variant]} class="h-5 w-5 shrink-0" />
					<div class="flex-1 text-sm leading-5">{t.message}</div>
					<button
						class="ml-2 text-white/80 hover:text-white cursor-pointer"
						onclick={() => toasts.dismissToast(t.id)}
						aria-label="Cerrar"
					>
						<Icon name="close" class="h-4 w-4" />
					</button>
				</div>
			</div>
		{/each}
	</div>
</div>

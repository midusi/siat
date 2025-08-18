<script lang="ts">
	import { dialogStore, closeDialog, type DialogState } from '$lib/dialog';
	import { fade, scale } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';

	function variantClass(variant: DialogState['variant']): string {
		if (variant === 'danger')
			return 'border-red-600/50 bg-red-600/15 hover:bg-red-600/25 text-red-100';
		if (variant === 'success')
			return 'border-green-500/40 bg-green-400/12 hover:bg-green-400/20 text-green-100';
		if (variant === 'warning')
			return 'border-amber-400/40 bg-amber-300/12 hover:bg-amber-300/20 text-amber-100';
		if (variant === 'info')
			return 'border-sky-400/40 bg-sky-300/12 hover:bg-sky-300/20 text-sky-100';
		return 'border-white/20 bg-white/10 hover:bg-white/20 text-white/90';
	}

	let dialog: DialogState | null = null;

	function onKeydown(e: KeyboardEvent) {
		if (!dialog) return;
		if (e.key === 'Escape') {
			if (dialog.type === 'alert') {
				dialog.resolve();
			} else if (dialog.type === 'confirm') {
				dialog.resolve(false);
			}
			closeDialog();
		}
	}

	function handleConfirm() {
		if (!dialog) return;
		if (dialog.type === 'alert') {
			dialog.resolve();
		} else {
			dialog.resolve(true);
		}
		closeDialog();
	}

	function handleCancel() {
		if (!dialog) return;
		if (dialog.type === 'confirm') {
			dialog.resolve(false);
		}
		closeDialog();
	}

	function handleOverlayKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			handleCancel();
		}
	}

	onMount(() => {
		const unsub = dialogStore.subscribe((v) => {
			dialog = v;
			if (browser) {
				document.body.style.overflow = v ? 'hidden' : '';
			}
		});
		return () => {
			unsub();
			if (browser) document.body.style.overflow = '';
		};
	});
</script>

<svelte:window on:keydown={onKeydown} />

{#if dialog}
	<div class="fixed inset-0 z-[100] flex items-center justify-center">
		<button
			class="absolute inset-0 bg-transparent"
			type="button"
			aria-label="Cerrar diálogo"
			on:click={handleCancel}
			on:keydown={handleOverlayKeydown}
		></button>
		<div
			class="relative mx-4 w-full max-w-md glass-strong frost frost-polarized border p-5 shadow-2xl"
			transition:scale={{ duration: 150, easing: cubicOut }}
		>
			{#if dialog.title}
				<h3 class="mb-3 text-lg font-semibold">{dialog.title}</h3>
			{/if}
			<p class="mb-5 opacity-90 whitespace-pre-line">{dialog.message}</p>
			<div class="flex justify-end gap-2">
				{#if dialog.type === 'confirm'}
					<button class="glass-button px-4 py-2" on:click={handleCancel}>
						{dialog.cancelText ?? 'Cancelar'}
					</button>
				{/if}
				<button
					class={`glass-button px-4 py-2 ${variantClass(dialog.variant)}`}
					on:click={handleConfirm}
				>
					{dialog.confirmText ?? 'Aceptar'}
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.z-100 {
		z-index: 100;
	}
</style>

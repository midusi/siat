<script lang="ts">
	import { dialogStore, closeDialog, type DialogState } from '$lib/dialog';
	import { fade, scale } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';

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
			class="absolute inset-0 bg-black/60"
			type="button"
			aria-label="Cerrar diálogo"
			on:click={handleCancel}
			on:keydown={handleOverlayKeydown}
		></button>
		<div
			class="relative mx-4 w-full max-w-md rounded-lg border border-gray-700 bg-[#1a202c] p-5 text-white shadow-2xl"
			transition:scale={{ duration: 150, easing: cubicOut }}
		>
			{#if dialog.title}
				<h3 class="mb-3 text-lg font-semibold">{dialog.title}</h3>
			{/if}
			<p class="mb-5 text-gray-300 whitespace-pre-line">{dialog.message}</p>
			<div class="flex justify-end gap-2">
				{#if dialog.type === 'confirm'}
					<button
						class="rounded bg-gray-600 px-4 py-2 text-white hover:bg-gray-500"
						on:click={handleCancel}
					>
						{dialog.cancelText ?? 'Cancelar'}
					</button>
				{/if}
				<button
					class={`rounded px-4 py-2 text-white hover:opacity-90 ${
						dialog.variant === 'danger'
							? 'bg-red-600'
							: dialog.variant === 'success'
								? 'bg-green-600'
								: dialog.variant === 'warning'
									? 'bg-amber-600'
									: dialog.variant === 'info'
										? 'bg-blue-600'
										: 'bg-blue-600'
					}`}
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

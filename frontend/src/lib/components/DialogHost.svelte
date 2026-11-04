<script lang="ts">
	import { dialog } from '$lib/dialog.svelte';
	import Modal from '$lib/components/Modal.svelte';
	import { VARIANT_CLASSES, VARIANT_HOVER_CLASSES } from '$lib/variant';

	let confirmButton: HTMLButtonElement | null = $state(null);

	$effect(() => {
		if (dialog.current) {
			confirmButton?.focus();
		}
	});

	const cancel = (): void => {
		dialog.close(false);
	};
</script>

<Modal
	open={!!dialog.current}
	title={dialog.current?.title}
	label={dialog.current?.message}
	closable={false}
	dimmed={false}
	onclose={cancel}
>
	{#if dialog.current}
		{@const current = dialog.current}
		<p class="mb-5 opacity-90 whitespace-pre-line">{current.message}</p>
		<div class="flex justify-end gap-2">
			{#if current.type === 'confirm'}
				<button type="button" class="glass-button px-4 py-2" onclick={cancel}>
					{current.cancelText}
				</button>
			{/if}
			<button
				bind:this={confirmButton}
				type="button"
				class={[
					'glass-button px-4 py-2',
					VARIANT_CLASSES[current.variant],
					VARIANT_HOVER_CLASSES[current.variant]
				]}
				onclick={() => dialog.close(true)}
			>
				{current.confirmText}
			</button>
		</div>
	{/if}
</Modal>

<script lang="ts">
	let {
		checked = $bindable(false),
		id,
		labelledby,
		onLabel = '',
		offLabel = '',
		disabled = false
	}: {
		checked: boolean;
		id?: string;
		labelledby?: string;
		onLabel?: string;
		offLabel?: string;
		disabled?: boolean;
	} = $props();

	const text = $derived(checked ? onLabel : offLabel);
</script>

<button
	type="button"
	{id}
	role="switch"
	aria-checked={checked}
	aria-labelledby={labelledby}
	{disabled}
	onclick={() => (checked = !checked)}
	class="inline-flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
>
	<span
		class={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition-colors ${checked ? 'bg-green-500/40 border-green-400/50' : 'bg-white/10 border-white/25'}`}
	>
		<span
			class={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${checked ? 'translate-x-6' : 'translate-x-1'}`}
		></span>
	</span>
	{#if text}
		<span class="text-sm text-white/80">{text}</span>
	{/if}
</button>

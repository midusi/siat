<script lang="ts">
	let {
		id,
		label,
		value = $bindable(''),
		type = 'text',
		error = '',
		disabled = false
	}: {
		id: string;
		label: string;
		value: string;
		type?: 'text' | 'email';
		error?: string;
		disabled?: boolean;
	} = $props();
</script>

<div>
	<label for={id} class="block text-sm mb-1 text-white/80">{label}</label>
	<input
		{type}
		{id}
		bind:value
		{disabled}
		class="glass-input disabled:opacity-60 disabled:cursor-not-allowed"
		class:border-red-500={error}
	/>
	{#if error}
		<p class="text-red-400 text-xs mt-1">{error}</p>
	{/if}
</div>

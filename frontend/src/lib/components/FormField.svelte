<script lang="ts">
	type Props = {
		disabled?: boolean;
		error?: string;
		id: string;
		label: string;
		type?: 'text' | 'email';
		value: string;
	};

	let {
		disabled = false,
		error = '',
		id,
		label,
		type = 'text',
		value = $bindable('')
	}: Props = $props();
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

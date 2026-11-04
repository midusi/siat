<script lang="ts">
	import type { FullAutoFill } from 'svelte/elements';

	type Props = {
		autocomplete?: FullAutoFill;
		disabled?: boolean;
		error?: string;
		id?: string;
		label: string;
		type?: 'text' | 'email';
		value: string;
	};

	const generatedId: string = $props.id();

	let {
		autocomplete,
		disabled = false,
		error = '',
		id = generatedId,
		label,
		type = 'text',
		value = $bindable('')
	}: Props = $props();

	const errorId: string = $derived(`${id}-error`);
</script>

<div>
	<label for={id} class="block text-sm mb-1 text-white/80">{label}</label>
	<input
		{type}
		{id}
		{autocomplete}
		bind:value
		{disabled}
		class="glass-input disabled:opacity-60 disabled:cursor-not-allowed"
		class:input-error={error}
		aria-invalid={!!error}
		aria-describedby={error ? errorId : undefined}
	/>
	{#if error}
		<p id={errorId} class="mt-1 text-sm text-red-400">{error}</p>
	{/if}
</div>

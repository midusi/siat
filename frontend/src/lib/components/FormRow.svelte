<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		children,
		error,
		for: htmlFor,
		label
	}: {
		children: Snippet;
		error?: string;
		for: string;
		label: string;
	} = $props();
</script>

<div class="flex flex-col space-y-2">
	<label for={htmlFor} class="text-lg">{label}</label>
	{@render children()}
	{#if error}
		<span class="text-red-300/90 text-xs">{error}</span>
	{/if}
	<div class="border-t glass-divider mt-2"></div>
</div>

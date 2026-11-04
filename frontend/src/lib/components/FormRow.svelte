<script lang="ts">
	import type { Snippet } from 'svelte';

	type Props = {
		children: Snippet;
		error?: string;
		for: string;
		label: string;
		required?: boolean;
	};

	let { children, error, for: htmlFor, label, required = false }: Props = $props();
</script>

<div class="flex flex-col space-y-2">
	<label for={htmlFor} class="text-lg">
		{label}
		{#if required}<span aria-hidden="true">*</span>{/if}
	</label>
	{@render children()}
	{#if error}
		<p id="{htmlFor}-error" class="mt-1 text-sm text-red-400">{error}</p>
	{/if}
	<div class="border-t glass-divider mt-2"></div>
</div>

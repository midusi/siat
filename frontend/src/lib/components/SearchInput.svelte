<script lang="ts">
	import Icon from './Icon.svelte';

	type Props = {
		placeholder?: string;
		ref?: HTMLInputElement | null;
		value: string;
	};

	let { placeholder = 'Buscar...', ref = $bindable(null), value = $bindable('') }: Props = $props();
</script>

<div class="relative">
	<Icon name="search" class="h-5 w-5 absolute left-3 top-1/2 -translate-y-1/2 text-white/60" />
	<input
		type="text"
		bind:this={ref}
		{value}
		oninput={(e) => (value = e.currentTarget.value)}
		{placeholder}
		class="glass-input !pl-10"
	/>
</div>

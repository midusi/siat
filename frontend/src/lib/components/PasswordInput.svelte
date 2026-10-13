<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';

	let {
		label,
		value = $bindable(''),
		error = '',
		autocomplete = 'current-password',
		children
	}: {
		label: string;
		value: string;
		error?: string;
		autocomplete?: 'current-password' | 'new-password';
		children?: Snippet;
	} = $props();

	const id = $props.id();
	const errorId = `${id}-error`;
	let visible = $state(false);
</script>

<div>
	<label class="block text-sm mb-1 text-white/80" for={id}>{label}</label>
	<div class="relative">
		<input
			{id}
			type={visible ? 'text' : 'password'}
			class="glass-input pr-10"
			class:input-error={error}
			{autocomplete}
			aria-invalid={!!error}
			aria-describedby={error ? errorId : undefined}
			bind:value
		/>
		<button
			type="button"
			class="absolute inset-y-0 right-0 px-3 text-white/75 hover:text-white cursor-pointer"
			onclick={() => (visible = !visible)}
			aria-label="Mostrar contraseña"
			aria-pressed={visible}
		>
			<Icon name={visible ? 'eye-off' : 'eye'} />
		</button>
	</div>
	{#if error}
		<p id={errorId} class="mt-1 text-sm text-red-400">{error}</p>
	{/if}
	{@render children?.()}
</div>

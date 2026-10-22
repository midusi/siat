<script lang="ts">
	import PasswordInput from './PasswordInput.svelte';

	let {
		newPassword = $bindable(''),
		confirmPassword = $bindable(''),
		errorNew = '',
		errorConfirm = '',
		newLabel = 'Nueva contraseña',
		confirmLabel = 'Confirmar nueva contraseña',
		showRequirements = true
	}: {
		newPassword: string;
		confirmPassword: string;
		errorNew?: string;
		errorConfirm?: string;
		newLabel?: string;
		confirmLabel?: string;
		showRequirements?: boolean;
	} = $props();

	const segments = [0, 1, 2, 3];
	const strengthLabels = ['Muy débil', 'Débil', 'Media', 'Fuerte', 'Muy fuerte'];
	const strengthColors = [
		'bg-red-500',
		'bg-orange-500',
		'bg-yellow-500',
		'bg-green-500',
		'bg-emerald-600'
	];

	const getStrengthScore = (pwd: string): number => {
		let score = 0;
		if (pwd.length >= 8) {
			score++;
		}
		if (/[A-Z]/.test(pwd) && /[a-z]/.test(pwd)) {
			score++;
		}
		if (/\d/.test(pwd)) {
			score++;
		}
		if (/[^A-Za-z0-9]/.test(pwd)) {
			score++;
		}
		return score;
	};

	const score = $derived(getStrengthScore(newPassword));
</script>

<div class="space-y-5">
	<PasswordInput
		label={newLabel}
		bind:value={newPassword}
		error={errorNew}
		autocomplete="new-password"
	>
		<div class="mt-2">
			<div class="flex gap-1">
				{#each segments as i (i)}
					<div
						class="h-1.5 flex-1 rounded {i < score ? strengthColors[score] : 'bg-white/12'}"
					></div>
				{/each}
			</div>
			<p class="mt-1 text-xs text-white/70">
				Fuerza: <span class="font-medium text-gray-300">{strengthLabels[score]}</span>
			</p>
		</div>
		{#if showRequirements}
			<p class="mt-1 text-xs text-white/70">
				Requisitos mínimos: 6+ caracteres, incluir letras y números.
			</p>
		{/if}
	</PasswordInput>

	<PasswordInput
		label={confirmLabel}
		bind:value={confirmPassword}
		error={errorConfirm}
		autocomplete="new-password"
	/>
</div>

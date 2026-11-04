<script lang="ts">
	import { MIN_PASSWORD_LENGTH } from '$lib/validation/user';
	import PasswordInput from '$lib/components/PasswordInput.svelte';

	type Props = {
		confirmLabel?: string;
		confirmPassword: string;
		errorConfirm?: string;
		errorNew?: string;
		newLabel?: string;
		newPassword: string;
		showRequirements?: boolean;
	};

	const LOWERCASE_REGEX: RegExp = /[a-z]/;
	const NUMBER_REGEX: RegExp = /\d/;
	const STRENGTH_COLORS: Array<string> = [
		'bg-red-500',
		'bg-orange-500',
		'bg-yellow-500',
		'bg-green-500',
		'bg-emerald-600'
	];
	const STRENGTH_LABELS: Array<string> = ['Muy débil', 'Débil', 'Media', 'Fuerte', 'Muy fuerte'];
	const SEGMENT_COUNT: number = STRENGTH_LABELS.length - 1;
	const STRONG_LENGTH: number = 8;
	const SYMBOL_REGEX: RegExp = /[^A-Za-z0-9]/;
	const UPPERCASE_REGEX: RegExp = /[A-Z]/;

	let {
		confirmLabel = 'Confirmar nueva contraseña',
		confirmPassword = $bindable(''),
		errorConfirm = '',
		errorNew = '',
		newLabel = 'Nueva contraseña',
		newPassword = $bindable(''),
		showRequirements = true
	}: Props = $props();

	const score: number = $derived.by((): number => {
		const conditions: Array<boolean> = [
			newPassword.length >= STRONG_LENGTH,
			NUMBER_REGEX.test(newPassword),
			SYMBOL_REGEX.test(newPassword),
			UPPERCASE_REGEX.test(newPassword) && LOWERCASE_REGEX.test(newPassword)
		];
		return conditions.filter(Boolean).length;
	});
</script>

<div class="space-y-5">
	<PasswordInput
		label={newLabel}
		bind:value={newPassword}
		error={errorNew}
		autocomplete="new-password"
	>
		{#if newPassword}
			<div class="mt-2">
				<div class="flex gap-1">
					{#each { length: SEGMENT_COUNT }, index (index)}
						<div
							class={[
								'h-1.5 flex-1 rounded',
								index < score ? STRENGTH_COLORS[score] : 'bg-white/12'
							]}
						></div>
					{/each}
				</div>
				<p class="mt-1 text-xs text-white/70">
					Fuerza: <span class="font-medium text-white/90">{STRENGTH_LABELS[score]}</span>
				</p>
			</div>
		{/if}
		{#if showRequirements}
			<p class="mt-1 text-xs text-white/70">
				Requisitos mínimos: {MIN_PASSWORD_LENGTH}+ caracteres, incluir letras y números.
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

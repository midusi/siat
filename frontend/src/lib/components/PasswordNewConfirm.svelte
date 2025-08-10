<script lang="ts">
	// Reusable password fields with strength meter and visibility toggles
	export let newPassword: string = '';
	export let confirmPassword: string = '';
	export let errorNew: string = '';
	export let errorConfirm: string = '';
	// Labels can be customized if needed
	export let newLabel = 'Nueva contraseña';
	export let confirmLabel = 'Confirmar nueva contraseña';
	export let showRequirements = true;

	let showNew = false;
	let showConfirm = false;
	const segments = [0, 1, 2, 3];

	function getStrength(pwd: string) {
		let score = 0;
		if (pwd.length >= 8) score++;
		if (/[A-Z]/.test(pwd) && /[a-z]/.test(pwd)) score++;
		if (/\d/.test(pwd)) score++;
		if (/[^A-Za-z0-9]/.test(pwd)) score++;
		const labels = ['Muy débil', 'Débil', 'Media', 'Fuerte', 'Muy fuerte'];
		const colors = [
			'bg-red-500',
			'bg-orange-500',
			'bg-yellow-500',
			'bg-green-500',
			'bg-emerald-600'
		];
		return { score, label: labels[score] ?? labels[0], color: colors[score] ?? colors[0] };
	}

	$: strength = getStrength(newPassword);

	function inputClass(hasError: boolean) {
		return (
			'w-full bg-[#2d3748] text-white rounded px-3 py-2 border focus:outline-none focus:ring-2 focus:ring-blue-500 ' +
			(hasError ? 'border-red-500' : 'border-gray-700')
		);
	}
	function labelClass() {
		return 'block text-sm font-medium text-gray-200 mb-1';
	}
	function helpClass() {
		return 'mt-1 text-xs text-gray-400';
	}
	function errorTextClass() {
		return 'mt-1 text-sm text-red-400';
	}
</script>

<!-- New password -->
<div class="space-y-5">
	<div>
		<label class={labelClass()}>{newLabel}</label>
		<div class="relative">
			<input
				type={showNew ? 'text' : 'password'}
				class={inputClass(!!errorNew)}
				bind:value={newPassword}
				autocomplete="new-password"
			/>
			<button
				type="button"
				class="absolute inset-y-0 right-0 pr-3 text-gray-400 hover:text-gray-200"
				onclick={() => (showNew = !showNew)}
				aria-label="Mostrar u ocultar contraseña"
			>
				<svg
					class="h-5 w-5"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
					<circle cx="12" cy="12" r="3" />
				</svg>
			</button>
		</div>
		<!-- Strength bar -->
		<div class="mt-2">
			<div class="flex gap-1">
				{#each segments as i}
					<div
						class={i < strength.score
							? `h-1.5 flex-1 rounded ${strength.color}`
							: 'h-1.5 flex-1 rounded bg-gray-700'}
					></div>
				{/each}
			</div>
			<p class={helpClass()}>
				Fuerza: <span class="font-medium text-gray-300">{strength.label}</span>
			</p>
		</div>
		{#if errorNew}
			<p class={errorTextClass()}>{errorNew}</p>
		{/if}
		{#if showRequirements}
			<p class={helpClass()}>Requisitos mínimos: 6+ caracteres, incluir letras y números.</p>
		{/if}
	</div>

	<!-- Confirm password -->
	<div>
		<label class={labelClass()}>{confirmLabel}</label>
		<div class="relative">
			<input
				type={showConfirm ? 'text' : 'password'}
				class={inputClass(!!errorConfirm)}
				bind:value={confirmPassword}
				autocomplete="new-password"
			/>
			<button
				type="button"
				class="absolute inset-y-0 right-0 pr-3 text-gray-400 hover:text-gray-200"
				onclick={() => (showConfirm = !showConfirm)}
				aria-label="Mostrar u ocultar contraseña"
			>
				<svg
					class="h-5 w-5"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
					<circle cx="12" cy="12" r="3" />
				</svg>
			</button>
		</div>
		{#if errorConfirm}
			<p class={errorTextClass()}>{errorConfirm}</p>
		{/if}
	</div>
</div>

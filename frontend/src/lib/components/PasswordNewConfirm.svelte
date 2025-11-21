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

	// field ids for a11y label association
	const newId = `pwd_${Math.random().toString(36).slice(2, 8)}`;
	const confirmId = `pwdc_${Math.random().toString(36).slice(2, 8)}`;

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
		return `glass-input pr-10 ${hasError ? 'border-red-500/70 ring-1 ring-red-500/30' : ''}`;
	}
	function labelClass() {
		return 'block mb-1 text-sm text-white/80';
	}
	function helpClass() {
		return 'mt-1 text-xs text-white/70';
	}
	function errorTextClass() {
		return 'mt-1 text-sm text-red-400';
	}
</script>

<!-- New password -->
<div class="space-y-5">
	<div>
		<label class={labelClass()} for={newId}>{newLabel}</label>
		<div class="relative">
			<input
				type={showNew ? 'text' : 'password'}
				class={inputClass(!!errorNew)}
				id={newId}
				bind:value={newPassword}
				autocomplete="new-password"
			/>
			<button
				type="button"
				class="absolute inset-y-0 right-0 px-3 text-white/75 hover:text-white focus:outline-none cursor-pointer"
				onclick={() => (showNew = !showNew)}
				aria-label="Mostrar u ocultar contraseña"
				aria-pressed={showNew}
			>
				{#if showNew}
					<!-- eye-off -->
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
						<path d="M3 3l18 18" />
					</svg>
				{:else}
					<!-- eye -->
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
				{/if}
			</button>
		</div>
		<!-- Strength bar -->
		<div class="mt-2">
			<div class="flex gap-1">
				{#each segments as i}
					<div
						class={i < strength.score
							? `h-1.5 flex-1 rounded ${strength.color}`
							: 'h-1.5 flex-1 rounded bg-white/12'}
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
		<label class={labelClass()} for={confirmId}>{confirmLabel}</label>
		<div class="relative">
			<input
				type={showConfirm ? 'text' : 'password'}
				class={inputClass(!!errorConfirm)}
				id={confirmId}
				bind:value={confirmPassword}
				autocomplete="new-password"
			/>
			<button
				type="button"
				class="absolute inset-y-0 right-0 px-3 text-white/75 hover:text-white focus:outline-none cursor-pointer"
				onclick={() => (showConfirm = !showConfirm)}
				aria-label="Mostrar u ocultar contraseña"
				aria-pressed={showConfirm}
			>
				{#if showConfirm}
					<!-- eye-off -->
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
						<path d="M3 3l18 18" />
					</svg>
				{:else}
					<!-- eye -->
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
				{/if}
			</button>
		</div>
		{#if errorConfirm}
			<p class={errorTextClass()}>{errorConfirm}</p>
		{/if}
	</div>
</div>

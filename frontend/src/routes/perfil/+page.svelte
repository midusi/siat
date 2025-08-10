<script lang="ts">
	import { apiFetch } from '$lib/api';
	import { goto } from '$app/navigation';

	let current_password = $state('');
	let new_password = $state('');
	let confirm_password = $state('');

	let errors = $state<{ current?: string; new?: string; confirm?: string; general?: string }>({});
	let success = $state('');
	let submitting = $state(false);
	let showCurrent = $state(false);
	let showNew = $state(false);
	let showConfirm = $state(false);

	const segments = [0, 1, 2, 3];
	const strength = $derived(getStrength(new_password));

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

	function inputClass(hasError: boolean) {
		return (
			'w-full bg-[#2d3748] text-white rounded px-3 py-2 border focus:outline-none focus:ring-2 focus:ring-amber-500 ' +
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

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!validate()) return;
		submitting = true;
		try {
			const res = await apiFetch('/user/me/change-password', {
				method: 'POST',
				body: JSON.stringify({ current_password, new_password, confirm_password })
			});
			if (res.status === 204 || res.ok) {
				await apiFetch('/auth/logout', { method: 'POST', headers: { 'X-CSRF-Token': '1' } });
				success = 'Contraseña cambiada con éxito. Vas a ser redirigido al inicio de sesión.';
				setTimeout(() => goto('/login'), 900);
				return;
			}
			const data = await res.json().catch(() => ({}));
			errors.general = data?.detail ?? 'No se pudo cambiar la contraseña';
		} catch (err) {
			errors.general = 'Error de red';
		} finally {
			submitting = false;
		}
	}

	function validate(): boolean {
		errors = {};
		success = '';
		let ok = true;
		if (!current_password) {
			errors.current = 'Ingresá tu contraseña actual';
			ok = false;
		}
		if (!new_password) {
			errors.new = 'Ingresá la nueva contraseña';
			ok = false;
		}
		if (new_password && new_password.length < 6) {
			errors.new = 'La contraseña debe tener al menos 6 caracteres';
			ok = false;
		}
		if (new_password && (!/[A-Za-z]/.test(new_password) || !/\d/.test(new_password))) {
			errors.new = 'Debe incluir letras y números';
			ok = false;
		}
		if (!confirm_password) {
			errors.confirm = 'Confirmá la nueva contraseña';
			ok = false;
		}
		if (new_password && confirm_password && new_password !== confirm_password) {
			errors.confirm = 'Las contraseñas no coinciden';
			ok = false;
		}
		return ok;
	}
</script>

<div class="max-w-3xl mx-auto p-6">
	<h1 class="text-2xl font-semibold text-gray-100 mb-2">Tu perfil</h1>
	<p class="text-gray-400 mb-6">
		Actualizá tu contraseña. Por seguridad, se cerrará tu sesión luego del cambio.
	</p>

	<section class="bg-[#12151c] rounded-lg p-6 border border-gray-700 shadow-lg">
		<div class="flex items-center gap-2 mb-4">
			<svg
				class="w-5 h-5 text-amber-400"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
				><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path
					d="M7 11V7a5 5 0 0 1 10 0v4"
				/></svg
			>
			<h2 class="text-lg font-medium text-gray-100">Cambiar contraseña</h2>
		</div>

		{#if errors.general}
			<div
				class="rounded-md border border-red-800 bg-red-900/30 text-red-200 px-4 py-3 text-sm mb-4"
			>
				{errors.general}
			</div>
		{/if}
		{#if success}
			<div
				class="rounded-md border border-emerald-800 bg-emerald-900/30 text-emerald-200 px-4 py-3 text-sm mb-4"
			>
				{success}
			</div>
		{/if}

		<form onsubmit={handleSubmit} class="space-y-5">
			<!-- Current password -->
			<div>
				<label class={labelClass()}>Contraseña actual</label>
				<div class="relative">
					<input
						type={showCurrent ? 'text' : 'password'}
						class={inputClass(!!errors.current)}
						bind:value={current_password}
						autocomplete="current-password"
					/>
					<button
						type="button"
						class="absolute inset-y-0 right-0 pr-3 text-gray-400 hover:text-gray-200"
						onclick={() => (showCurrent = !showCurrent)}
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
							><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle
								cx="12"
								cy="12"
								r="3"
							/></svg
						>
					</button>
				</div>
				{#if errors.current}
					<p class={errorTextClass()}>{errors.current}</p>
				{/if}
			</div>

			<!-- New password -->
			<div>
				<label class={labelClass()}>Nueva contraseña</label>
				<div class="relative">
					<input
						type={showNew ? 'text' : 'password'}
						class={inputClass(!!errors.new)}
						bind:value={new_password}
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
							><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle
								cx="12"
								cy="12"
								r="3"
							/></svg
						>
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
				{#if errors.new}
					<p class={errorTextClass()}>{errors.new}</p>
				{/if}
				<p class={helpClass()}>Requisitos mínimos: 6+ caracteres, incluir letras y números.</p>
			</div>

			<!-- Confirm password -->
			<div>
				<label class={labelClass()}>Confirmar nueva contraseña</label>
				<div class="relative">
					<input
						type={showConfirm ? 'text' : 'password'}
						class={inputClass(!!errors.confirm)}
						bind:value={confirm_password}
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
							><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle
								cx="12"
								cy="12"
								r="3"
							/></svg
						>
					</button>
				</div>
				{#if errors.confirm}
					<p class={errorTextClass()}>{errors.confirm}</p>
				{/if}
			</div>

			<div class="flex items-center gap-3 pt-2">
				<button
					type="submit"
					class="inline-flex items-center gap-2 bg-amber-500 hover:bg-amber-600 text-white px-4 py-2 rounded-md disabled:opacity-60 disabled:cursor-not-allowed"
					disabled={submitting}
				>
					{#if submitting}
						<svg class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none"
							><circle
								class="opacity-25"
								cx="12"
								cy="12"
								r="10"
								stroke="currentColor"
								stroke-width="4"
							></circle><path
								class="opacity-75"
								fill="currentColor"
								d="M4 12a8 8 0 018-8v4A4 4 0 004 12z"
							></path></svg
						>
						Guardando...
					{:else}
						Guardar cambios
					{/if}
				</button>
				<button
					type="button"
					class="inline-flex items-center gap-2 px-4 py-2 rounded-md border border-gray-700 text-gray-200 hover:bg-gray-800"
					onclick={() => goto('/')}>Cancelar</button
				>
			</div>
		</form>
	</section>
</div>

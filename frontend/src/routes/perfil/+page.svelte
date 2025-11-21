<script lang="ts">
	import { apiFetch } from '$lib/api';
	import { goto } from '$app/navigation';
	import { showSuccess } from '$lib/toast';
	import PasswordNewConfirm from '$lib/components/PasswordNewConfirm.svelte';
	import Spinner from '$lib/components/Spinner.svelte';

	let current_password = $state('');
	let new_password = $state('');
	let confirm_password = $state('');

	let errors = $state<{ current?: string; new?: string; confirm?: string; general?: string }>({});
	let submitting = $state(false);
	let showCurrent = $state(false);
	const currId = `curr_${Math.random().toString(36).slice(2, 8)}`;

	function inputClass(hasError: boolean) {
		return `glass-input pr-10 ${hasError ? 'border-red-500/70 ring-1 ring-red-500/30' : ''}`;
	}

	function labelClass() {
		return 'block text-sm mb-1 text-white/80';
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
				showSuccess('Contraseña cambiada con éxito. Vas a ser redirigido al inicio de sesión.');
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

<div class="page-container max-w-3xl">
	<h1 class="heading-1 mb-1">Tu perfil</h1>
	<p class="text-white/70 mb-6">
		Actualizá tu contraseña. Por seguridad, se cerrará tu sesión luego del cambio.
	</p>

	<section class="glass-card max-w-3xl mx-auto p-6 sm:p-8 overflow-hidden">
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
				class="rounded-md border border-red-600/50 bg-red-600/15 text-red-100 px-4 py-3 text-sm mb-4"
			>
				{errors.general}
			</div>
		{/if}

		<form onsubmit={handleSubmit} class="space-y-5">
			<!-- Current password -->
			<div>
				<label class={labelClass()} for={currId}>Contraseña actual</label>
				<div class="relative">
					<input
						type={showCurrent ? 'text' : 'password'}
						class={inputClass(!!errors.current)}
						id={currId}
						bind:value={current_password}
						autocomplete="current-password"
					/>
					<button
						type="button"
						class="absolute inset-y-0 right-0 px-3 text-white/75 hover:text-white cursor-pointer"
						onclick={() => (showCurrent = !showCurrent)}
						aria-label="Mostrar u ocultar contraseña"
						aria-pressed={showCurrent}
					>
						{#if showCurrent}
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
				{#if errors.current}
					<p class={errorTextClass()}>{errors.current}</p>
				{/if}
			</div>

			<!-- New/Confirm password using reusable component -->
			<PasswordNewConfirm
				bind:newPassword={new_password}
				bind:confirmPassword={confirm_password}
				errorNew={errors.new ?? ''}
				errorConfirm={errors.confirm ?? ''}
			/>

			<div class="flex items-center gap-3 pt-2">
				<button
					type="submit"
					class="glass-button btn-success disabled:opacity-60 disabled:cursor-not-allowed"
					disabled={submitting}
				>
					{#if submitting}
						<Spinner size={16} />
						Guardando...
					{:else}
						Guardar cambios
					{/if}
				</button>
				<button type="button" class="glass-button" onclick={() => goto('/')}>Cancelar</button>
			</div>
		</form>
	</section>
</div>

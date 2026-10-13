<script lang="ts">
	import { ApiError } from '$lib/services/errors';
	import { changePassword } from '$lib/services/profile';
	import {
		emptyChangePasswordErrors,
		hasErrors,
		validateChangePassword
	} from '$lib/validation/user';
	import { goto } from '$app/navigation';
	import { logout } from '$lib/services/auth';
	import Icon from '$lib/components/Icon.svelte';
	import PasswordInput from '$lib/components/PasswordInput.svelte';
	import PasswordNewConfirm from '$lib/components/PasswordNewConfirm.svelte';
	import { showSuccess } from '$lib/toast';
	import Spinner from '$lib/components/Spinner.svelte';

	let current_password = $state('');
	let new_password = $state('');
	let confirm_password = $state('');

	let errors = $state(emptyChangePasswordErrors());
	let submitting = $state(false);

	const handleSubmit = async (e: SubmitEvent) => {
		e.preventDefault();

		errors = validateChangePassword(current_password, new_password, confirm_password);
		if (hasErrors(errors)) {
			return;
		}

		submitting = true;
		try {
			await changePassword(current_password, new_password, confirm_password);
			await logout();
			showSuccess('Contraseña cambiada con éxito. Vas a ser redirigido al inicio de sesión.');
			setTimeout(() => goto('/login'), 900);
		} catch (err) {
			errors.general =
				err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor';
		} finally {
			submitting = false;
		}
	};
</script>

<div class="page-container max-w-3xl">
	<h1 class="heading-1 mb-1">Tu perfil</h1>
	<p class="text-white/70 mb-6">
		Actualizá tu contraseña. Por seguridad, se cerrará tu sesión luego del cambio.
	</p>

	<section class="glass-card p-6 sm:p-8">
		<div class="flex items-center gap-2 mb-4">
			<Icon name="lock" class="w-5 h-5 text-amber-400" />
			<h2 class="text-lg font-medium text-gray-100">Cambiar contraseña</h2>
		</div>

		{#if errors.general}
			<div class="alert-danger px-4 py-3 text-sm mb-4" role="alert">{errors.general}</div>
		{/if}

		<form onsubmit={handleSubmit} class="space-y-5">
			<PasswordInput
				label="Contraseña actual"
				bind:value={current_password}
				error={errors.current}
				autocomplete="current-password"
			/>

			<PasswordNewConfirm
				bind:newPassword={new_password}
				bind:confirmPassword={confirm_password}
				errorNew={errors.new}
				errorConfirm={errors.confirm}
			/>

			<div class="flex items-center gap-3 pt-2">
				<button type="submit" class="glass-button btn-success" disabled={submitting}>
					{#if submitting}
						<Spinner size={16} />
						Guardando...
					{:else}
						Guardar cambios
					{/if}
				</button>
				<a href="/" class="glass-button">Cancelar</a>
			</div>
		</form>
	</section>
</div>

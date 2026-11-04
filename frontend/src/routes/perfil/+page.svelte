<script lang="ts">
	import { changePassword } from '$lib/services/profile';
	import {
		emptyChangePasswordErrors,
		hasErrors,
		validateChangePassword
	} from '$lib/validation/user';
	import { errorMessage } from '$lib/services/errors';
	import { goto } from '$app/navigation';
	import Icon from '$lib/components/Icon.svelte';
	import { LOGIN_PATH } from '$lib/constants';
	import { logout } from '$lib/services/auth';
	import PasswordInput from '$lib/components/PasswordInput.svelte';
	import PasswordNewConfirm from '$lib/components/PasswordNewConfirm.svelte';
	import { showSuccess } from '$lib/toast.svelte';
	import Spinner from '$lib/components/Spinner.svelte';

	import type { ChangePasswordErrors } from '$lib/validation/user';

	const REDIRECT_DELAY_MS: number = 900;

	let confirmPassword: string = $state('');
	let currentPassword: string = $state('');
	let errors: ChangePasswordErrors = $state(emptyChangePasswordErrors());
	let newPassword: string = $state('');
	let submitting: boolean = $state(false);

	const handleSubmit = async (e: SubmitEvent): Promise<void> => {
		e.preventDefault();

		errors = validateChangePassword(currentPassword, newPassword, confirmPassword);
		if (hasErrors(errors)) {
			return;
		}

		submitting = true;
		try {
			await changePassword(currentPassword, newPassword, confirmPassword);
			await logout();
			showSuccess('Contraseña cambiada con éxito. Vas a ser redirigido al inicio de sesión.');
			setTimeout(() => goto(LOGIN_PATH), REDIRECT_DELAY_MS);
		} catch (err) {
			errors.general = errorMessage(err);
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
				bind:value={currentPassword}
				error={errors.current}
				autocomplete="current-password"
			/>

			<PasswordNewConfirm
				bind:newPassword
				bind:confirmPassword
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

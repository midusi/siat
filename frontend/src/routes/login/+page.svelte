<script lang="ts">
	import './login.css';
	import { ApiError } from '$lib/services/errors';
	import { goto } from '$app/navigation';
	import { login } from '$lib/services/auth';
	import { page } from '$app/state';
	import { safeNext } from '$lib/redirect';
	import Spinner from '$lib/components/Spinner.svelte';

	let error: string | null = $state(null);
	let isSubmitting: boolean = $state(false);
	let password: string = $state('');
	let username: string = $state('');

	const handleLogin = async (): Promise<void> => {
		error = null;
		isSubmitting = true;
		try {
			await login(username, password);
			await goto(safeNext(page.url.searchParams.get('next')));
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'No se pudo conectar con el servidor';
		} finally {
			isSubmitting = false;
		}
	};
</script>

<div class="min-h-screen flex items-center justify-center">
	<div class="w-full max-w-md px-6">
		<div class="mb-12 flex flex-col items-center">
			<div class="logo-circle w-24 h-24 rounded-full mb-4"></div>
			<h1 class="text-center font-semibold">
				<span class="block text-xl opacity-90">ANÁLISIS DE</span>
				<span class="logo-gradient-text block text-3xl">TRÁNSITO</span>
			</h1>
		</div>

		<form
			class="space-y-4 glass-card p-6 border"
			onsubmit={(e) => {
				e.preventDefault();
				void handleLogin();
			}}
		>
			{#if error}
				<div class="alert-danger p-2" role="alert">{error}</div>
			{/if}
			<input
				type="text"
				name="username"
				autocomplete="username"
				placeholder="Usuario"
				aria-label="Usuario"
				required
				bind:value={username}
				class="glass-input block"
			/>
			<input
				type="password"
				name="password"
				autocomplete="current-password"
				placeholder="Contraseña"
				aria-label="Contraseña"
				required
				bind:value={password}
				class="glass-input block"
			/>

			<button
				type="submit"
				class="glass-button btn-primary w-full justify-center gap-2 py-3 font-medium"
				disabled={isSubmitting}
			>
				{#if isSubmitting}
					<Spinner size={16} />
					Iniciando sesión...
				{:else}
					Iniciar Sesión
				{/if}
			</button>
		</form>
	</div>
</div>

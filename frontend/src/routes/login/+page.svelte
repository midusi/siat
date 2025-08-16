<!-- src/routes/login/+page.svelte -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { apiFetch } from '$lib/api';
	import Spinner from '$lib/components/Spinner.svelte';

	let username = $state('');
	let password = $state('');
	let error = $state<string | null>(null);
	let isSubmitting = $state(false);

	async function handleLogin(): Promise<void> {
		error = null;
		try {
			isSubmitting = true;
			const res = await apiFetch('/auth/login', {
				method: 'POST',
				body: JSON.stringify({ username, password })
			});
			if (res.ok) {
				const next = new URLSearchParams($page.url.search).get('next') ?? '/';
				await goto(next);
			} else if (res.status === 401) {
				error = 'Credenciales inválidas';
			} else {
				error = 'Error de autenticación';
			}
		} catch (e) {
			error = 'No se pudo conectar con el servidor';
		} finally {
			isSubmitting = false;
		}
	}
</script>

<div class="min-h-screen bg-[#1a1e2a] flex items-center justify-center">
	<!-- Formulario de login centrado -->
	<div class="w-full max-w-md px-6">
		<!-- Logo agrandado -->
		<div class="mb-16 flex flex-col items-center justify-center">
			<!-- Círculo del logo agrandado -->
			<div
				class="w-24 h-24 rounded-full border-4 border-amber-400 flex items-center justify-center mb-4"
			>
				<div class="w-16 h-16 rounded-full bg-amber-400 opacity-30"></div>
			</div>
			<!-- Texto del logo agrandado -->
			<div class="text-center">
				<div class="text-amber-400 font-bold text-xl">ANÁLISIS DE</div>
				<div class="text-amber-400 font-bold text-3xl">TRÁNSITO</div>
			</div>
		</div>

		<!-- Formulario -->
		<form
			class="space-y-4"
			onsubmit={(e) => {
				e.preventDefault();
				void handleLogin();
			}}
		>
			{#if error}
				<div class="p-2 bg-red-900/40 text-red-200 rounded">{error}</div>
			{/if}
			<!-- Campo Usuario -->
			<div>
				<input
					type="text"
					id="username"
					placeholder="Usuario"
					bind:value={username}
					class="w-full bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
				/>
			</div>

			<!-- Campo Contraseña -->
			<div>
				<input
					type="password"
					id="password"
					placeholder="Contraseña"
					bind:value={password}
					class="w-full bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
				/>
			</div>

			<!-- Botón de inicio de sesión -->
			<button
				type="submit"
				class="w-full bg-blue-500 hover:bg-blue-600 text-white py-3 rounded-md font-medium transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
				disabled={isSubmitting}
			>
				{#if isSubmitting}
					<Spinner size={16} />
					Iniciando sesión...
				{:else}
					Iniciar Sesión
				{/if}
			</button>

			<!-- Credenciales de prueba -->
			<div class="mt-6 p-4 bg-[#2d3748] rounded-md text-gray-300 text-sm">
				<div class="font-medium mb-1">Credenciales de prueba:</div>
				<div>Usuario: admin</div>
				<div>Contraseña: admin</div>
			</div>
		</form>
	</div>
</div>

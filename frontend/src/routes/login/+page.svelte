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

<div class="min-h-screen flex items-center justify-center">
	<!-- Formulario de login centrado -->
	<div class="w-full max-w-md px-6">
		<!-- Logo agrandado -->
		<div class="mb-12 flex flex-col items-center justify-center">
			<!-- Círculo del logo agrandado -->
			<div
				class="w-24 h-24 rounded-full flex items-center justify-center mb-4"
				style="background:
					radial-gradient(circle at 30% 30%, hsl(var(--accent1) / 0.35), transparent 60%),
					radial-gradient(circle at 70% 70%, hsl(var(--accent2) / 0.35), transparent 60%);
					box-shadow: inset 0 0 0 4px rgba(255,255,255,0.18);"
			></div>
			<!-- Texto del logo agrandado -->
			<div class="text-center" style="color: hsl(var(--foreground));">
				<div class="font-semibold text-xl opacity-90">ANÁLISIS DE</div>
				<div
					class="font-semibold text-3xl"
					style="background: linear-gradient(90deg, hsl(var(--accent1)), hsl(var(--accent2))); -webkit-background-clip: text; background-clip: text; color: transparent;"
				>
					TRÁNSITO
				</div>
			</div>
		</div>

		<!-- Formulario -->
		<form
			class="space-y-4 glass-card p-6 border"
			onsubmit={(e) => {
				e.preventDefault();
				void handleLogin();
			}}
		>
			{#if error}
				<div class="p-2 btn-danger rounded border">{error}</div>
			{/if}
			<!-- Campo Usuario -->
			<div>
				<input
					type="text"
					id="username"
					placeholder="Usuario"
					bind:value={username}
					class="glass-input"
				/>
			</div>

			<!-- Campo Contraseña -->
			<div>
				<input
					type="password"
					id="password"
					placeholder="Contraseña"
					bind:value={password}
					class="glass-input"
				/>
			</div>

			<!-- Botón de inicio de sesión -->
			<button
				type="submit"
				class="w-full glass-button border-sky-400/40 bg-sky-300/10 hover:bg-sky-300/20 text-sky-100 py-3 rounded-md font-medium disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
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

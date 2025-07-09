<!-- src/routes/login/+page.svelte -->
<script lang="ts">
	import { goto } from '$app/navigation';

	// Estado para los campos del formulario
	let email = $state('');
	let password = $state('');

	// Función para manejar el inicio de sesión
	async function handleLogin(): Promise<void> {
		const response = await fetchApi('/api/login', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ email, password })
		});
		
		if (response.ok) {
			const user = await response.json();
			console.log('Login exitoso:', user);
			goto('/'); // Redirigir al dashboard
		} else {
			console.error('Error en login');
		}
	}

	// Función para recuperar contraseña
	function handleRecoverPassword(): void {
		// Aquí iría la lógica para recuperar contraseña
		console.log('Recuperando contraseña para:', email);
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
		<form class="space-y-4">
			<!-- Campo Email -->
			<div>
				<input
					type="email"
					id="email"
					placeholder="Correo"
					bind:value={email}
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
				type="button"
				onclick={handleLogin}
				class="w-full bg-blue-500 hover:bg-blue-600 text-white py-3 rounded-md font-medium transition-colors"
			>
				Iniciar Sesión
			</button>

			<!-- Credenciales de prueba -->
			<div class="mt-6 p-4 bg-[#2d3748] rounded-md text-gray-300 text-sm">
				<div class="font-medium mb-1">Credenciales de prueba:</div>
				<div>Email: m@gmail.com</div>
				<div>Contraseña: 1234</div>
			</div>
		</form>

		<!-- Enlace para recuperar contraseña -->
		<div class="mt-6 text-center">
			<button
				type="button"
				onclick={handleRecoverPassword}
				class="text-blue-400 hover:text-blue-300 text-sm"
			>
				Recuperar Contraseña
			</button>
		</div>
	</div>
</div>

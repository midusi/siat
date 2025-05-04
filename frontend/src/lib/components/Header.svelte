<script lang="ts">
	// src/lib/components/Header.svelte

	// Información del usuario
	const userName: string = 'Facundo Quiroga';
	const userEmail: string = 'facundo.quiroga@ejemplo.com';

	// Estado para controlar si el menú desplegable está abierto o cerrado
	let isDropdownOpen = $state(false);

	// Función para alternar el estado del menú desplegable
	function toggleDropdown(event: MouseEvent): void {
		event.stopPropagation();
		isDropdownOpen = !isDropdownOpen;
	}

	// Función para cerrar el menú desplegable al hacer clic fuera de él
	function closeDropdown(event: MouseEvent): void {
		const target = event.target as HTMLElement;
		if (!target.closest('.user-dropdown-container')) {
			isDropdownOpen = false;
		}
	}

	// Añadir un event listener para cerrar el dropdown al hacer clic fuera
	$effect(() => {
		if (typeof window !== 'undefined') {
			if (isDropdownOpen) {
				window.addEventListener('click', closeDropdown);
			} else {
				window.removeEventListener('click', closeDropdown);
			}
		}

		// Limpieza al desmontar el componente
		return () => {
			if (typeof window !== 'undefined') {
				window.removeEventListener('click', closeDropdown);
			}
		};
	});

	// Función para manejar el cierre de sesión
	function handleLogout(): void {
		// Aquí iría la lógica para cerrar sesión
		console.log('Cerrando sesión...');
		// Por ejemplo: redireccionar a la página de login
		// window.location.href = '/login';
	}
</script>

<header class="bg-[#0f1216] text-white py-3 px-4 flex justify-between items-center">
	<div class="flex items-center gap-3">
		<div class="w-8 h-8 rounded-full bg-yellow-500 flex items-center justify-center">
			<!-- Círculo amarillo con borde -->
			<div class="w-7 h-7 rounded-full border-2 border-[#0f1216]"></div>
		</div>
		<div>
			<span class="text-yellow-500 font-bold">ANÁLISIS DE</span>
			<br />
			<span class="text-yellow-500 font-bold text-lg leading-none">TRÁNSITO</span>
		</div>
	</div>

	<div class="flex items-center gap-2 relative user-dropdown-container">
		<span>{userName}</span>
		<!-- Botón del icono de usuario -->
		<button
			class="w-8 h-8 bg-gray-500 rounded-full flex items-center justify-center focus:outline-none"
			onclick={toggleDropdown}
			aria-label="Menú de usuario"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-5 w-5 text-white"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
				/>
			</svg>
		</button>

		<!-- Menú desplegable -->
		{#if isDropdownOpen}
			<div
				class="absolute right-0 top-full mt-2 w-64 bg-white rounded-md shadow-lg z-50 overflow-hidden"
			>
				<!-- Información del usuario -->
				<div class="p-4 bg-gray-100 border-b">
					<p class="font-medium text-gray-800">{userName}</p>
					<p class="text-sm text-gray-600">{userEmail}</p>
				</div>

				<!-- Opciones del menú -->
				<div class="p-2">
					<button
						class="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-100 rounded-md flex items-center"
						onclick={handleLogout}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="h-4 w-4 mr-2"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
							/>
						</svg>
						Cerrar sesión
					</button>
				</div>
			</div>
		{/if}
	</div>
</header>

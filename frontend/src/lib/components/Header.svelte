<script lang="ts">
	// src/lib/components/Header.svelte
	import { goto } from '$app/navigation';
	import { apiFetch } from '$lib/api';

	let { user } = $props<{ user: App.Locals['user'] }>();

	let isDropdownOpen = $state(false);

	function toggleDropdown(event: MouseEvent): void {
		event.stopPropagation();
		isDropdownOpen = !isDropdownOpen;
	}

	function closeDropdown(event: MouseEvent): void {
		const target = event.target as HTMLElement;
		if (!target.closest('.user-dropdown-container')) {
			isDropdownOpen = false;
		}
	}

	$effect(() => {
		if (typeof window !== 'undefined') {
			if (isDropdownOpen) {
				window.addEventListener('click', closeDropdown);
			} else {
				window.removeEventListener('click', closeDropdown);
			}
		}
		return () => {
			if (typeof window !== 'undefined') {
				window.removeEventListener('click', closeDropdown);
			}
		};
	});

	async function handleLogout(): Promise<void> {
		const res = await apiFetch('/auth/logout', {
			method: 'POST',
			headers: { 'X-CSRF-Token': '1' }
		});
		if (res.ok || res.status === 204) {
			await goto('/login');
		}
	}

	function goChangePassword(): void {
		isDropdownOpen = false;
		goto('/perfil');
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
		<span>{user?.first_name ?? user?.username}</span>
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
					<p class="font-medium text-gray-800">{user?.first_name} {user?.last_name}</p>
					<p class="text-sm text-gray-600">{user?.email}</p>
				</div>

				<!-- Opciones del menú -->
				<div class="p-2">
					<button
						class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md flex items-center"
						onclick={goChangePassword}
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 11c0-1.657-1.343-3-3-3S6 9.343 6 11v2H5a2 2 0 00-2 2v3a2 2 0 002 2h10a2 2 0 002-2v-3a2 2 0 00-2-2h-1v-2z" />
						</svg>
						Cambiar contraseña
					</button>
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

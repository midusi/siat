<script lang="ts">
	import { goto } from '$app/navigation';
	import { apiFetch } from '$lib/api';
	import Spinner from '$lib/components/Spinner.svelte';
	import { portal } from '$lib/actions/portal';

	let { user } = $props<{ user: App.Locals['user'] }>();

	let isDropdownOpen = $state(false);
	let isLoggingOut = $state(false);
	let btnEl: HTMLButtonElement | null = null;
	let dropdownTop = $state(0);
	let dropdownRight = $state(0);

	function toggleDropdown(event: MouseEvent): void {
		event.stopPropagation();
		isDropdownOpen = !isDropdownOpen;
		if (isDropdownOpen) positionDropdown();
	}

	function closeDropdown(event: MouseEvent): void {
		const target = event.target as HTMLElement;
		if (!target.closest('.user-dropdown-container') && !target.closest('.user-menu')) {
			isDropdownOpen = false;
		}
	}

	function positionDropdown() {
		if (!btnEl) return;
		const rect = btnEl.getBoundingClientRect();
		dropdownTop = Math.round(rect.bottom + 8);
		dropdownRight = Math.round(window.innerWidth - rect.right);
	}

	$effect(() => {
		if (typeof window !== 'undefined') {
			if (isDropdownOpen) {
				window.addEventListener('click', closeDropdown);
				window.addEventListener('resize', positionDropdown);
				window.addEventListener('scroll', positionDropdown, { passive: true });
			} else {
				window.removeEventListener('click', closeDropdown);
				window.removeEventListener('resize', positionDropdown);
				window.removeEventListener('scroll', positionDropdown);
			}
		}
		return () => {
			if (typeof window !== 'undefined') {
				window.removeEventListener('click', closeDropdown);
				window.removeEventListener('resize', positionDropdown);
				window.removeEventListener('scroll', positionDropdown);
			}
		};
	});

	async function handleLogout(): Promise<void> {
		isLoggingOut = true;
		const res = await apiFetch('/auth/logout', {
			method: 'POST',
			headers: { 'X-CSRF-Token': '1' }
		});
		if (res.ok || res.status === 204) await goto('/login');
		isLoggingOut = false;
	}

	function goChangePassword(): void {
		isDropdownOpen = false;
		goto('/perfil');
	}
</script>

<header
	class="sticky top-[var(--layout-gap)] z-40 glass-strong frost px-4 py-3 flex justify-between items-center border glass-divider mx-[var(--layout-gap)] rounded-xl"
	style="height: var(--header-height);"
>
	<div class="flex items-center gap-3 select-none">
		<div class="w-9 h-9 rounded-full bg-yellow-500/90 flex items-center justify-center shadow-md">
			<div class="w-8 h-8 rounded-full border-2 border-[#0f1216]"></div>
		</div>
		<div class="leading-tight">
			<span class="text-yellow-400 font-semibold tracking-wide">ANÁLISIS DE</span>
			<br />
			<span class="text-yellow-400 font-bold text-lg">TRÁNSITO</span>
		</div>
	</div>

	<div class="flex items-center gap-3 relative user-dropdown-container">
		<span class="opacity-90">{user?.first_name ?? user?.username}</span>
		<button
			class="w-9 h-9 glass rounded-full flex items-center justify-center focus:outline-none hover:bg-white/10 transition-colors cursor-pointer"
			bind:this={btnEl}
			onclick={toggleDropdown}
			aria-label="Menú de usuario"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-5 w-5 text-white/90"
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

		{#if isDropdownOpen}
			<div
				use:portal
				class="user-menu glass-strong frost frost-polarized z-50 overflow-hidden"
				style={`position: fixed; top: ${dropdownTop}px; right: ${dropdownRight}px; width: 16rem;`}
			>
				<div class="p-4 border-b glass-divider">
					<p class="font-medium">{user?.first_name} {user?.last_name}</p>
					<p class="text-sm opacity-80">{user?.email}</p>
				</div>
				<div class="p-2 flex flex-col gap-2">
					<button
						class="w-full text-left px-4 py-2 text-sm rounded-md flex items-center glass-button"
						onclick={goChangePassword}
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
								d="M12 11c0-1.657-1.343-3-3-3S6 9.343 6 11v2H5a2 2 0 00-2 2v3a2 2 0 002 2h10a2 2 0 002-2v-3a2 2 0 00-2-2h-1v-2z"
							/>
						</svg>
						Cambiar contraseña
					</button>
					<button
						class="w-full text-left px-4 py-2 text-sm rounded-lg flex items-center gap-2 btn-danger disabled:opacity-60"
						disabled={isLoggingOut}
						onclick={handleLogout}
					>
						{#if isLoggingOut}
							<Spinner size={16} />
							Cerrando sesión...
						{:else}
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
						{/if}
					</button>
				</div>
			</div>
		{/if}
	</div>
</header>

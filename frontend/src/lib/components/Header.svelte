<script lang="ts">
	import { goto } from '$app/navigation';
	import Icon from '$lib/components/Icon.svelte';
	import { LOGIN_PATH } from '$lib/constants';
	import { logout } from '$lib/services/auth';
	import { portal } from '$lib/actions/portal';
	import Spinner from '$lib/components/Spinner.svelte';

	type MenuPosition = { top: number; right: number };
	type Props = { user: App.Locals['user'] };

	const MENU_OFFSET_PX: number = 8;

	let { user }: Props = $props();

	let buttonEl: HTMLButtonElement | null = $state(null);
	let containerEl: HTMLDivElement | null = $state(null);
	let isLoggingOut: boolean = $state(false);
	let isMenuOpen: boolean = $state(false);
	let menuEl: HTMLDivElement | null = $state(null);
	let menuPosition: MenuPosition = $state({ top: 0, right: 0 });

	const displayName: string = $derived(user?.first_name || user?.username || '');
	const fullName: string = $derived([user?.first_name, user?.last_name].filter(Boolean).join(' '));

	const updatePosition = (): void => {
		if (!buttonEl) {
			return;
		}
		const bounds: DOMRect = buttonEl.getBoundingClientRect();
		menuPosition = {
			top: Math.round(bounds.bottom + MENU_OFFSET_PX),
			right: Math.round(window.innerWidth - bounds.right)
		};
	};

	const closeMenu = (): void => {
		isMenuOpen = false;
	};

	const toggleMenu = (): void => {
		if (!isMenuOpen) {
			updatePosition();
		}
		isMenuOpen = !isMenuOpen;
	};

	const handleWindowClick = (event: MouseEvent): void => {
		if (!isMenuOpen) {
			return;
		}
		const target: Node = event.target as Node;
		if (!containerEl?.contains(target) && !menuEl?.contains(target)) {
			closeMenu();
		}
	};

	const handleWindowKeydown = (event: KeyboardEvent): void => {
		if (isMenuOpen && event.key === 'Escape') {
			closeMenu();
			buttonEl?.focus();
		}
	};

	const handleViewportChange = (): void => {
		if (isMenuOpen) {
			updatePosition();
		}
	};

	const handleLogout = async (): Promise<void> => {
		isLoggingOut = true;
		try {
			if (await logout()) {
				await goto(LOGIN_PATH);
			}
		} finally {
			isLoggingOut = false;
		}
	};
</script>

<svelte:window
	onclick={handleWindowClick}
	onkeydown={handleWindowKeydown}
	onresize={handleViewportChange}
	onscrollcapture={handleViewportChange}
/>

<header
	class="sticky top-[var(--layout-gap)] z-40 glass-strong frost px-4 py-3 flex justify-between items-center border glass-divider mx-[var(--layout-gap)] rounded-xl"
	style="height: var(--header-height);"
>
	<div class="flex items-center gap-3 select-none">
		<div class="w-9 h-9 rounded-full bg-yellow-500/90 flex items-center justify-center shadow-md">
			<div class="w-8 h-8 rounded-full border-2 border-[#0f1216]"></div>
		</div>
		<div class="leading-tight text-yellow-400">
			<span class="block font-semibold tracking-wide">ANÁLISIS DE</span>
			<span class="block font-bold text-lg">TRÁNSITO</span>
		</div>
	</div>

	<div class="flex items-center gap-3" bind:this={containerEl}>
		<span class="opacity-90">{displayName}</span>
		<button
			class="w-9 h-9 glass rounded-full flex items-center justify-center focus:outline-none hover:bg-white/10 transition-colors cursor-pointer"
			bind:this={buttonEl}
			type="button"
			aria-label="Menú de usuario"
			aria-expanded={isMenuOpen}
			aria-haspopup="menu"
			onclick={toggleMenu}
		>
			<Icon name="user" class="h-5 w-5 text-white/90" />
		</button>

		{#if isMenuOpen}
			<div
				use:portal
				bind:this={menuEl}
				class="fixed w-64 glass-strong frost frost-polarized z-50 overflow-hidden"
				role="menu"
				style:top="{menuPosition.top}px"
				style:right="{menuPosition.right}px"
			>
				<div class="p-4 border-b glass-divider">
					<p class="font-medium">{fullName}</p>
					<p class="text-sm opacity-80">{user?.email}</p>
				</div>
				<div class="p-2 flex flex-col gap-2">
					<a
						href="/perfil"
						class="w-full text-left px-4 py-2 text-sm rounded-lg flex items-center gap-2 glass-button"
						role="menuitem"
						onclick={closeMenu}
					>
						<Icon name="lock" class="h-4 w-4" />
						Cambiar contraseña
					</a>
					<button
						class="w-full text-left px-4 py-2 text-sm rounded-lg flex items-center gap-2 btn-danger disabled:opacity-60"
						type="button"
						role="menuitem"
						disabled={isLoggingOut}
						onclick={handleLogout}
					>
						{#if isLoggingOut}
							<Spinner size={16} />
							Cerrando sesión...
						{:else}
							<Icon name="logout" class="h-4 w-4" />
							Cerrar sesión
						{/if}
					</button>
				</div>
			</div>
		{/if}
	</div>
</header>

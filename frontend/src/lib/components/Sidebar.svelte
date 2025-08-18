<script lang="ts">
	import { page } from '$app/stores';
	let { user } = $props<{ user: App.Locals['user'] }>();

	// Lista de elementos del menú
	const menuItems = [
		{
			id: 'tareas',
			label: 'Tareas',
			path: '/',
			icon: `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
			  	</svg>`
		},
		{
			id: 'tareas-archivadas',
			label: 'Archivadas',
			path: '/tareas/archivadas',
			icon: `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7a2 2 0 012-2h14a2 2 0 012 2v0a2 2 0 01-2 2H5a2 2 0 01-2-2v0zm0 4a2 2 0 012-2h14a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6z" />
				</svg>`
		},
		{
			id: 'admin',
			label: 'Admin',
			path: '/admin',
			icon: `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
				</svg>`
		}
	];

	// Determinar la ruta actual para resaltar el elemento activo (runes)
	let currentPath = $derived($page.url.pathname);

	// Animated rail state
	let containerEl: HTMLElement | null = null;
	let railTop = $state(0);
	let railHeight = $state(0);
	let railVisible = $state(false);

	function isAllowed(itemId: string) {
		return itemId !== 'admin' || user?.role === 'ROLE_ADMIN';
	}

	function updateRail() {
		if (!containerEl) return;
		const idx = menuItems.findIndex((it) => it.path === currentPath && isAllowed(it.id));
		if (idx === -1) {
			railVisible = false;
			return;
		}
		// Compute index among rendered (allowed) items
		const allowedBefore = menuItems.slice(0, idx).filter((it) => isAllowed(it.id)).length;
		const links = containerEl.querySelectorAll('a.sidebar-link');
		const el = links[allowedBefore] as HTMLElement | undefined;
		if (!el) {
			railVisible = false;
			return;
		}
		// Use offsetTop/offsetHeight for stable positioning within container
		railTop = el.offsetTop;
		railHeight = el.offsetHeight;
		railVisible = true;
	}

	$effect(() => {
		// recompute when route changes
		currentPath;
		queueMicrotask(updateRail);
	});

	// Ensure rail measures after the container element binds
	$effect(() => {
		containerEl;
		queueMicrotask(updateRail);
	});

	// Manage window resize listener with cleanup
	$effect(() => {
		if (typeof window === 'undefined') return;
		window.addEventListener('resize', updateRail);
		return () => window.removeEventListener('resize', updateRail);
	});
</script>

<!-- Sidebar - Oculto en móvil, visible en tablet/desktop -->
<aside
	class="relative w-[72px] flex-col items-center py-4 shrink-0 hidden md:flex glass-card border-r glass-divider mt-[var(--layout-gap)]"
	style="height: calc(100vh - var(--layout-gap) - var(--header-height) - var(--layout-gap) - var(--layout-bottom-gap));"
	bind:this={containerEl}
>
	{#if railVisible}
		<div class="sidebar-rail" style={`top:${railTop}px; height:${railHeight}px;`}></div>
	{/if}
	{#each menuItems as item}
		{#if item.id !== 'admin' || user?.role === 'ROLE_ADMIN'}
			<a
				href={item.path}
				class="sidebar-link w-full flex flex-col items-center py-4 text-center relative {currentPath ===
				item.path
					? 'text-amber-300 opacity-100'
					: 'text-gray-400 opacity-90 hover:text-gray-200 hover:opacity-100 hover:bg-white/5'}"
			>
				<div class="mb-1">
					{@html item.icon}
				</div>
				<span
					class="uppercase opacity-90 {item.id === 'tareas-archivadas'
						? 'text-[10px] tracking-normal'
						: 'text-[11px] tracking-wide'}">{item.label}</span
				>
			</a>
		{/if}
	{/each}
</aside>

<style>
	.sidebar-rail {
		position: absolute;
		left: 0;
		width: 2px;
		background: rgba(252, 211, 77, 0.95); /* amber-300 */
		box-shadow:
			0 0 6px rgba(252, 211, 77, 0.75),
			0 0 12px rgba(252, 211, 77, 0.55),
			0 0 18px rgba(252, 211, 77, 0.35);
		border-radius: 2px;
		transition:
			top 220ms ease,
			height 220ms ease;
		pointer-events: none;
	}

	a.sidebar-link {
		transition:
			color 220ms ease,
			opacity 220ms ease,
			background-color 220ms ease;
	}
</style>

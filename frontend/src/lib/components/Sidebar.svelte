<script lang="ts">
	import { page } from '$app/stores';
	export let user: App.Locals['user'];

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
			id: 'admin',
			label: 'Admin',
			path: '/admin',
			icon: `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
				</svg>`
		}
	];

	// Determinar la ruta actual para resaltar el elemento activo
	$: currentPath = $page.url.pathname;
</script>

<!-- Sidebar - Oculto en móvil, visible en tablet/desktop -->
<aside
	class="bg-[#1a1e2a] w-16 min-h-screen flex-col items-center py-4 shrink-0 border-r border-gray-800 hidden md:flex"
>
	{#each menuItems as item}
		{#if item.id !== 'admin' || user?.role === 'ROLE_ADMIN'}
			<a
				href={item.path}
				class="w-full flex flex-col items-center py-4 text-center {currentPath === item.path
					? 'text-amber-400'
					: 'text-gray-400 hover:text-gray-200'}"
			>
				<div class="mb-1">
					{@html item.icon}
				</div>
				<span class="text-xs">{item.label}</span>
			</a>
		{/if}
	{/each}
</aside>

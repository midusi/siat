<script lang="ts">
	let { children } = $props();
	import '../app.css';
	import Header from '$lib/components/Header.svelte';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import { page } from '$app/stores';

	// Definición de tipos para los elementos del menú
	interface MenuItem {
		id: string;
		label: string;
		path: string;
		icon: string;
	}

	// Lista de elementos del menú
	const menuItems: MenuItem[] = [
		{
			id: 'tareas',
			label: 'Tareas',
			path: '/',
			icon: `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
			  </svg>`
		},
		{
			id: 'revisar',
			label: 'Revisar',
			path: '/revisar',
			icon: `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
			  </svg>`
		},
		{
			id: 'ajustes',
			label: 'Ajustes',
			path: '/ajustes',
			icon: `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
			  </svg>`
		}
	];

	let isLoginPage = $derived($page.url.pathname === '/login');

	// Función para obtener la ruta actual (segura para SSR)
	function isActive(path: string): boolean {
		if (typeof window === 'undefined') return path === '/';
		return path === window.location.pathname;
	}
</script>

<div class="flex flex-col min-h-screen">
	{#if !isLoginPage}
		<Header />
		<div class="flex flex-1">
			<Sidebar />
			<main class="flex-1 overflow-x-auto">
				{@render children()}
			</main>
		</div>
	{:else}
		<main class="flex-1 overflow-x-auto">
			{@render children()}
		</main>
	{/if}
</div>

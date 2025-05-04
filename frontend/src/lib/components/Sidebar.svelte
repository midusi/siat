<script lang="ts">
	import { page } from '$app/stores';
	import type { MenuItem } from '$lib/types';

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

	// Determinar la ruta actual para resaltar el elemento activo
	$: currentPath = $page.url.pathname;
</script>

<aside
	class="bg-[#1a1e2a] w-16 min-h-screen flex flex-col items-center py-4 shrink-0 border-r border-gray-800"
>
	{#each menuItems as item}
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
	{/each}
</aside>

<script lang="ts">
	import './Sidebar.css';
	import Icon from '$lib/components/Icon.svelte';
	import { isAdmin } from '$lib/roles';
	import { page } from '$app/state';

	import type { MenuItem } from '$lib/types/menu';
	import type { User } from '$lib/types/user';

	type Props = {
		user: User | null;
	};
	type Rail = { top: number; height: number };

	const MENU_ITEMS: Array<MenuItem> = [
		{
			id: 'tareas',
			label: 'Tareas',
			path: '/',
			icon: 'monitor'
		},
		{
			id: 'tareas-archivadas',
			label: 'Archivadas',
			path: '/tareas/archivadas',
			icon: 'archive'
		},
		{
			id: 'admin',
			label: 'Admin',
			path: '/admin',
			icon: 'key',
			adminOnly: true
		}
	];

	let { user }: Props = $props();

	let linkEls: Record<string, HTMLAnchorElement> = $state({});
	let rail: Rail | null = $state(null);

	const currentPath: string = $derived(page.url.pathname);
	const visibleItems: Array<MenuItem> = $derived(
		MENU_ITEMS.filter((item) => !item.adminOnly || isAdmin(user?.role))
	);
	const activeItem: MenuItem | undefined = $derived(
		visibleItems.find((item) => item.path === currentPath)
	);

	$effect(() => {
		updateRail();
	});

	const updateRail = (): void => {
		const activeLink: HTMLAnchorElement | undefined = activeItem
			? linkEls[activeItem.id]
			: undefined;
		rail = activeLink ? { top: activeLink.offsetTop, height: activeLink.offsetHeight } : null;
	};
</script>

<svelte:window onresize={updateRail} />

<aside
	class="relative w-[72px] flex-col items-center py-4 shrink-0 hidden md:flex glass-card border-r glass-divider mt-[var(--layout-gap)]"
	style="height: calc(100vh - var(--layout-gap) - var(--header-height) - var(--layout-gap) - var(--layout-bottom-gap));"
>
	{#if rail}
		<div class="sidebar-rail" style="top: {rail.top}px; height: {rail.height}px;"></div>
	{/if}
	{#each visibleItems as item (item.id)}
		{@const active = item === activeItem}
		<a
			href={item.path}
			bind:this={linkEls[item.id]}
			aria-current={active ? 'page' : undefined}
			class={[
				'sidebar-link w-full flex flex-col items-center py-4 text-center relative',
				active
					? 'text-amber-300 opacity-100'
					: 'text-gray-400 opacity-90 hover:text-gray-200 hover:opacity-100 hover:bg-white/5'
			]}
		>
			<div class="mb-1">
				<Icon name={item.icon} />
			</div>
			<span
				class={[
					'uppercase opacity-90',
					item.id === 'tareas-archivadas'
						? 'text-[10px] tracking-normal'
						: 'text-[11px] tracking-wide'
				]}>{item.label}</span
			>
		</a>
	{/each}
</aside>

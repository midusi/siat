<script lang="ts">
	let { children, data } = $props();
	import '../app.css';
	import Header from '$lib/components/Header.svelte';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import { page } from '$app/stores';
	import DialogHost from '$lib/components/DialogHost.svelte';
	import ToastHost from '$lib/components/ToastHost.svelte';

	const user = $derived(data.user);
	let isLoginPage = $derived($page.url.pathname === '/login');
</script>

<div class="flex flex-col min-h-screen">
	{#if !isLoginPage && user}
		<Header {user} />
		<div class="flex flex-1">
			<Sidebar {user} />
			<main class="flex-1 overflow-x-auto bg-[#1a1e2a] text-gray-100">
				{@render children()}
			</main>
		</div>
	{:else}
		<main class="flex-1 overflow-x-auto bg-[#1a1e2a] text-gray-100">
			{@render children()}
		</main>
	{/if}
	<DialogHost />
	<ToastHost />
</div>

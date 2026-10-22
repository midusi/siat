<script lang="ts">
	import '../app.css';
	import DialogHost from '$lib/components/DialogHost.svelte';
	import Header from '$lib/components/Header.svelte';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import ToastHost from '$lib/components/ToastHost.svelte';

	import type { LayoutProps } from './$types';

	let { children, data }: LayoutProps = $props();
</script>

<div class="flex flex-col min-h-screen app-background">
	{#if data.user}
		<Header user={data.user} />
		<div
			class="flex flex-1 gap-[var(--layout-gap)] px-[var(--layout-gap)] pb-[var(--layout-bottom-gap)] mt-[var(--layout-gap)] overflow-y-auto"
		>
			<Sidebar user={data.user} />
			<main class="flex-1 overflow-auto pt-[var(--layout-gap)]">
				{@render children()}
			</main>
		</div>
	{:else}
		<main class="flex-1 overflow-x-auto">
			{@render children()}
		</main>
	{/if}
	<DialogHost />
	<ToastHost />
</div>

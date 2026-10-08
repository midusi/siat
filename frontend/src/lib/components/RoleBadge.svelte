<script lang="ts">
	import type { Role } from '$lib/types/user';

	let { role }: { role: Role } = $props();

	const isAdmin = $derived(role === 'ROLE_ADMIN');
</script>

<span
	class={`px-2 py-1 rounded text-xs font-medium border ${isAdmin ? 'text-purple-200 bg-purple-400/15 border-purple-300/30' : 'text-sky-200 bg-sky-400/15 border-sky-300/30'}`}
>
	{isAdmin ? 'Admin' : 'Operador'}
</span>

<script lang="ts">
	import { ROLE_LABELS } from '$lib/roles';

	import type { Role } from '$lib/types/user';

	type Props = {
		role: Role;
	};

	const ROLE_CLASSES: Record<Role, string> = {
		ROLE_ADMIN: 'text-purple-200 bg-purple-400/15 border-purple-300/30',
		ROLE_OPERADOR: 'text-sky-200 bg-sky-400/15 border-sky-300/30'
	};

	let { role }: Props = $props();
</script>

<span class={['px-2 py-1 rounded text-xs font-medium border', ROLE_CLASSES[role]]}>
	{ROLE_LABELS[role]}
</span>

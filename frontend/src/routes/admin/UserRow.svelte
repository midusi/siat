<script lang="ts">
	import RoleBadge from '$lib/components/RoleBadge.svelte';
	import type { User } from '$lib/types/user';

	let {
		user,
		toggling,
		deleting,
		onedit,
		ontoggle,
		ondelete
	}: {
		user: User;
		toggling: boolean;
		deleting: boolean;
		onedit: (user: User) => void;
		ontoggle: (user: User) => void;
		ondelete: (userId: number) => void;
	} = $props();
</script>

<tr class="border-b glass-divider hover:bg-white/5 transition-colors">
	<td class="p-3">
		<span class="font-medium">#{user.id}</span>
	</td>
	<td class="p-3">
		{user.first_name}
		{user.last_name}
	</td>
	<td class="p-3">
		{user.email}
	</td>
	<td class="p-3">
		<div class="flex items-center">
			<RoleBadge role={user.role} />
		</div>
	</td>
	<td class="p-3">
		<button
			onclick={() => ontoggle(user)}
			aria-busy={toggling}
			disabled={toggling}
			class={`glass-button px-2 py-1 text-xs ${user.active ? 'btn-success' : 'btn-danger'} ${toggling ? 'opacity-50 cursor-not-allowed' : ''}`}
		>
			{user.active ? 'Activo' : 'Inactivo'}
		</button>
	</td>
	<td class="p-3">
		<div class="flex gap-2">
			<button
				onclick={() => onedit(user)}
				class="glass-button text-sm px-3 py-1"
				title="Editar usuario"
			>
				Editar
			</button>
			<button
				onclick={() => ondelete(user.id)}
				class="glass-button btn-danger text-sm px-3 py-1 disabled:opacity-50"
				title="Eliminar usuario"
				disabled={deleting}
			>
				Eliminar
			</button>
		</div>
	</td>
</tr>

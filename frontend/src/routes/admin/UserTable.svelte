<script lang="ts">
	import type { User } from '$lib/types/user';
	import UserRow from './UserRow.svelte';

	let {
		users,
		toggling,
		deleting,
		loadError = '',
		isFiltering = false,
		onedit,
		ontoggle,
		ondelete
	}: {
		users: User[];
		toggling: Record<number, boolean>;
		deleting: Record<number, boolean>;
		loadError?: string;
		isFiltering?: boolean;
		onedit: (user: User) => void;
		ontoggle: (user: User) => void;
		ondelete: (userId: number) => void;
	} = $props();
</script>

<div class="glass-card overflow-hidden">
	<table class="w-full border-collapse">
		<thead>
			<tr class="glass-surface text-white/90">
				<th class="p-3 text-left font-medium">ID</th>
				<th class="p-3 text-left font-medium">Nombre</th>
				<th class="p-3 text-left font-medium">Email</th>
				<th class="p-3 text-left font-medium">Rol</th>
				<th class="p-3 text-left font-medium">Estado</th>
				<th class="p-3 text-left font-medium">Acciones</th>
			</tr>
		</thead>
		<tbody>
			{#each users as user (user.id)}
				<UserRow
					{user}
					toggling={!!toggling[user.id]}
					deleting={!!deleting[user.id]}
					{onedit}
					{ontoggle}
					{ondelete}
				/>
			{/each}

			{#if users.length === 0}
				<tr>
					<td colspan="6" class="p-4 text-center text-white/70">
						{#if loadError}
							<span class="text-red-400">{loadError}</span>
						{:else if isFiltering}
							No se encontraron usuarios que coincidan con la búsqueda.
						{:else}
							No se encontraron usuarios.
						{/if}
					</td>
				</tr>
			{/if}
		</tbody>
	</table>
</div>

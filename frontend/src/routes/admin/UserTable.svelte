<script lang="ts">
	import UserRow from './UserRow.svelte';

	import type { PendingByUserId, User } from '$lib/types/user';

	type Props = {
		deleting: PendingByUserId;
		isFiltering?: boolean;
		loadError?: string;
		ondelete: (userId: number) => void;
		onedit: (user: User) => void;
		ontoggle: (user: User) => void;
		toggling: PendingByUserId;
		users: Array<User>;
	};

	const COLUMNS: Array<string> = ['ID', 'Nombre', 'Email', 'Rol', 'Estado', 'Acciones'];

	let {
		deleting,
		isFiltering = false,
		loadError = '',
		ondelete,
		onedit,
		ontoggle,
		toggling,
		users
	}: Props = $props();
</script>

<div class="glass-card overflow-x-auto">
	<table class="w-full border-collapse">
		<thead>
			<tr class="glass-surface text-white/90">
				{#each COLUMNS as column (column)}
					<th class="p-3 text-left font-medium">{column}</th>
				{/each}
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
					<td colspan={COLUMNS.length} class="p-4 text-center text-white/70">
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

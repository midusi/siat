<script lang="ts">
	import GlassSelect from '$lib/components/GlassSelect.svelte';
	import { onMount } from 'svelte';
	import PasswordNewConfirm from '$lib/components/PasswordNewConfirm.svelte';
	import { showAlert, showConfirm } from '$lib/dialog';
	import type { User, Role } from '$lib/types/user';
	import {
		changeUserStatus,
		createUser,
		deleteUser,
		fetchUsers,
		resetUserPassword,
		updateUser
	} from '$lib/services/users';

	let users = $state<User[]>([]);
	let loadError = $state('');
	let searchQuery = $state('');
	let showModal = $state(false);
	let editingUser = $state<User | null>(null);
	let newUser = $state<Omit<User, 'id'> & { password: string; confirm_password: string }>({
		username: '',
		email: '',
		role: 'ROLE_OPERADOR',
		first_name: '',
		last_name: '',
		active: true,
		password: '',
		confirm_password: ''
	});
	let formErrors = $state({
		first_name: '',
		last_name: '',
		email: '',
		username: '',
		password: '',
		confirm_password: '',
		general: ''
	});
	let submitting = $state(false);
	let toggling = $state<Record<number, boolean>>({});
	let deleting = $state<Record<number, boolean>>({});

	onMount(async () => {
		try {
			users = await fetchUsers();
		} catch (e) {
			console.error('Error de red al cargar usuarios', e);
			loadError = 'No se pudieron cargar los usuarios';
		}
	});

	const roleItems: { value: Role; label: string }[] = [
		{ value: 'ROLE_ADMIN', label: 'Admin' },
		{ value: 'ROLE_OPERADOR', label: 'Operador' }
	];
	const estadoItems = [
		{ value: 'Activo', label: 'Activo' },
		{ value: 'Inactivo', label: 'Inactivo' }
	];

	const filteredUsers = $derived.by(() => {
		const q = searchQuery.trim().toLowerCase();
		if (!q) {
			return users;
		}
		return users.filter(
			(u) =>
				`${u.first_name} ${u.last_name}`.toLowerCase().includes(q) ||
				u.email.toLowerCase().includes(q)
		);
	});

	const openCreateModal = (): void => {
		editingUser = null;
		newUser = {
			first_name: '',
			last_name: '',
			email: '',
			role: 'ROLE_OPERADOR',
			active: true,
			username: '',
			password: '',
			confirm_password: ''
		};
		formErrors = {
			first_name: '',
			last_name: '',
			email: '',
			username: '',
			password: '',
			confirm_password: '',
			general: ''
		};
		showModal = true;
	};

	const openEditModal = (user: User): void => {
		editingUser = user;
		newUser = {
			first_name: user.first_name,
			last_name: user.last_name,
			email: user.email,
			role: user.role,
			active: user.active,
			username: user.username,
			password: '',
			confirm_password: ''
		};
		formErrors = {
			first_name: '',
			last_name: '',
			email: '',
			username: '',
			password: '',
			confirm_password: '',
			general: ''
		};
		showModal = true;
	};

	const escapeClosesModal = (e: KeyboardEvent): void => {
		if (showModal && e.key === 'Escape') {
			closeModal();
		}
	};

	const closeModal = (): void => {
		if (submitting) {
			return;
		}
		showModal = false;
	};

	const validate = (): boolean => {
		formErrors = {
			first_name: '',
			last_name: '',
			email: '',
			username: '',
			password: '',
			confirm_password: '',
			general: ''
		};
		let ok = true;
		if (!newUser.first_name?.trim()) {
			formErrors.first_name = 'Requerido';
			ok = false;
		}
		if (!newUser.last_name?.trim()) {
			formErrors.last_name = 'Requerido';
			ok = false;
		}
		if (!newUser.email?.trim()) {
			formErrors.email = 'Requerido';
			ok = false;
		}
		if (!newUser.username?.trim()) {
			formErrors.username = 'Requerido';
			ok = false;
		}
		const shouldValidatePassword = !editingUser || newUser.password || newUser.confirm_password;
		if (shouldValidatePassword) {
			const pwd = newUser.password;
			if (!pwd) {
				formErrors.password = 'Requerido';
				ok = false;
			}
			if (!newUser.confirm_password) {
				formErrors.confirm_password = 'Requerido';
				ok = false;
			}
			if (pwd && (pwd.length < 6 || !/[A-Za-z]/.test(pwd) || !/\d/.test(pwd))) {
				formErrors.password =
					'La contraseña debe incluir letras y números y tener al menos 6 caracteres';
				ok = false;
			}
			if (pwd && newUser.confirm_password && pwd !== newUser.confirm_password) {
				formErrors.confirm_password = 'Las contraseñas no coinciden';
				ok = false;
			}
		}
		return ok;
	};

	const handleSubmit = async (event?: SubmitEvent) => {
		if (event?.preventDefault) {
			event.preventDefault();
		}
		if (!validate()) {
			return;
		}
		submitting = true;
		try {
			if (editingUser) {
				const current = editingUser;
				const updates: Record<string, unknown> = {};
				const fields = ['first_name', 'last_name', 'email', 'role'] as const;
				for (const field of fields) {
					if (newUser[field] !== current[field]) {
						updates[field] = newUser[field];
					}
				}

				if (Object.keys(updates).length > 0) {
					const updated = await updateUser(current.id, updates);
					users = users.map((u) => (u.id === updated.id ? updated : u));
				}

				if (newUser.active !== current.active) {
					const updated = await changeUserStatus(current.id, newUser.active);
					if (updated) {
						users = users.map((u) => (u.id === current.id ? updated : u));
					}
				}

				if (newUser.password) {
					await resetUserPassword(current.id, newUser.password, newUser.confirm_password);
				}

				showModal = false;
				return;
			}

			const created = await createUser({
				username: newUser.username,
				password: newUser.password,
				confirm_password: newUser.confirm_password,
				email: newUser.email,
				role: newUser.role,
				first_name: newUser.first_name,
				last_name: newUser.last_name,
				active: newUser.active
			});
			users = [...users, created];
			showModal = false;
		} catch (e) {
			formErrors.general = e instanceof Error ? e.message : 'Error de red';
		} finally {
			submitting = false;
		}
	};

	const toggleStatus = async (user: User): Promise<void> => {
		if (toggling[user.id]) {
			return;
		}
		const prev = user.active;
		const targetActive = !prev;
		toggling[user.id] = true;
		users = users.map((u) => (u.id === user.id ? { ...u, active: targetActive } : u));
		try {
			const updated = await changeUserStatus(user.id, targetActive);
			if (updated) {
				users = users.map((u) => (u.id === user.id ? updated : u));
			}
		} catch (e) {
			users = users.map((u) => (u.id === user.id ? { ...u, active: prev } : u));
			await showAlert({
				message: e instanceof Error ? e.message : 'No se pudo actualizar el estado',
				variant: 'danger'
			});
		} finally {
			toggling[user.id] = false;
		}
	};

	const removeUser = async (userId: number): Promise<void> => {
		if (deleting[userId]) {
			return;
		}
		const confirmed = await showConfirm({
			message:
				'¿Estás seguro de que deseas eliminar este usuario? Esta acción no se puede deshacer.',
			variant: 'danger',
			confirmText: 'Eliminar',
			cancelText: 'Cancelar'
		});
		if (!confirmed) {
			return;
		}
		deleting[userId] = true;
		const prev = users;
		users = users.filter((u) => u.id !== userId);
		try {
			await deleteUser(userId);
		} catch (e) {
			users = prev;
			await showAlert({ message: 'Error de red al eliminar usuario', variant: 'danger' });
		} finally {
			deleting[userId] = false;
		}
	};
</script>

<svelte:window onkeydown={escapeClosesModal} />

<div class="page-container">
	<div class="mb-6 flex items-center justify-between">
		<div class="flex items-center gap-2">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-5 w-5 text-amber-300"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
				/>
			</svg>
			<h1 class="heading-1">Administración de Usuarios</h1>
		</div>
		<button onclick={openCreateModal} class="glass-button btn-success px-3 py-2">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-4 w-4 mr-1"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
			</svg>
			Nuevo Usuario
		</button>
	</div>

	<div class="mb-4 relative">
		<svg
			xmlns="http://www.w3.org/2000/svg"
			class="h-5 w-5 absolute left-3 top-1/2 -translate-y-1/2 text-white/60"
			fill="none"
			viewBox="0 0 24 24"
			stroke="currentColor"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				stroke-width="2"
				d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
			/>
		</svg>
		<input
			type="text"
			bind:value={searchQuery}
			placeholder="Buscar usuarios por nombre o email..."
			class="glass-input !pl-10"
		/>
	</div>

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
				{#each filteredUsers as user (user.id)}
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
								<span
									class={`px-2 py-1 rounded text-xs font-medium border ${user.role === 'ROLE_ADMIN' ? 'text-purple-200 bg-purple-400/15 border-purple-300/30' : 'text-sky-200 bg-sky-400/15 border-sky-300/30'}`}
								>
									{user.role === 'ROLE_ADMIN' ? 'Admin' : 'Operador'}
								</span>
							</div>
						</td>
						<td class="p-3">
							<button
								onclick={() => toggleStatus(user)}
								aria-busy={toggling[user.id]}
								disabled={toggling[user.id]}
								class={`glass-button px-2 py-1 text-xs ${user.active ? 'btn-success' : 'btn-danger'} ${toggling[user.id] ? 'opacity-50 cursor-not-allowed' : ''}`}
							>
								{user.active ? 'Activo' : 'Inactivo'}
							</button>
						</td>
						<td class="p-3">
							<div class="flex gap-2">
								<button
									onclick={() => openEditModal(user)}
									class="glass-button text-sm px-3 py-1"
									title="Editar usuario"
								>
									Editar
								</button>
								<button
									onclick={() => removeUser(user.id)}
									class="glass-button btn-danger text-sm px-3 py-1 disabled:opacity-50"
									title="Eliminar usuario"
									disabled={deleting[user.id]}
								>
									Eliminar
								</button>
							</div>
						</td>
					</tr>
				{/each}

				{#if filteredUsers.length === 0}
					<tr>
						<td colspan="6" class="p-4 text-center text-white/70">
							{#if loadError}
								<span class="text-red-400">{loadError}</span>
							{:else if searchQuery.trim()}
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

	{#if showModal}
		<div class="fixed inset-0 z-[100] flex items-center justify-center p-4">
			<button
				type="button"
				class="absolute inset-0 bg-black/40"
				aria-label="Cerrar"
				onclick={closeModal}
			></button>
			<div
				class="relative mx-4 w-full max-w-md glass-strong frost frost-polarized border p-6 shadow-2xl"
				role="dialog"
				aria-modal="true"
			>
				<button
					type="button"
					class="absolute top-3 right-3 text-white/70 hover:text-white"
					onclick={closeModal}
					aria-label="Cerrar"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-5 w-5"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>

				<h3 class="text-lg font-semibold mb-4">
					{editingUser ? 'Editar Usuario' : 'Nuevo Usuario'}
				</h3>

				<form class="space-y-4" onsubmit={handleSubmit}>
					<div class="grid grid-cols-2 gap-3">
						<div>
							<label for="first_name" class="block text-sm mb-1 text-white/80">Nombre</label>
							<input
								type="text"
								id="first_name"
								bind:value={newUser.first_name}
								class="glass-input"
								class:border-red-500={formErrors.first_name}
							/>
							{#if formErrors.first_name}
								<p class="text-red-400 text-xs mt-1">{formErrors.first_name}</p>
							{/if}
						</div>
						<div>
							<label for="last_name" class="block text-sm mb-1 text-white/80">Apellido</label>
							<input
								type="text"
								id="last_name"
								bind:value={newUser.last_name}
								class="glass-input"
								class:border-red-500={formErrors.last_name}
							/>
							{#if formErrors.last_name}
								<p class="text-red-400 text-xs mt-1">{formErrors.last_name}</p>
							{/if}
						</div>
					</div>

					<div>
						<label for="email" class="block text-sm mb-1 text-white/80">Email</label>
						<input
							type="email"
							id="email"
							bind:value={newUser.email}
							class="glass-input"
							class:border-red-500={formErrors.email}
						/>
						{#if formErrors.email}
							<p class="text-red-400 text-xs mt-1">{formErrors.email}</p>
						{/if}
					</div>

					<div>
						<label for="username" class="block text-sm mb-1 text-white/80">Usuario</label>
						<input
							type="text"
							id="username"
							bind:value={newUser.username}
							disabled={!!editingUser}
							class="glass-input disabled:opacity-60 hover:cursor-not-allowed"
							class:border-red-500={formErrors.username}
						/>
						{#if formErrors.username}
							<p class="text-red-400 text-xs mt-1">{formErrors.username}</p>
						{/if}
					</div>

					<PasswordNewConfirm
						bind:newPassword={newUser.password}
						bind:confirmPassword={newUser.confirm_password}
						errorNew={formErrors.password}
						errorConfirm={formErrors.confirm_password}
					/>

					<div>
						<label id="label-rol" for="rol" class="block text-sm mb-1 text-white/80">Rol</label>
						<GlassSelect
							id="rol"
							ariaLabel="Seleccionar rol"
							ariaLabelledby="label-rol"
							items={roleItems}
							value={newUser.role}
							onChange={(v) => (newUser.role = v as Role)}
						/>
					</div>

					<div>
						<label id="label-estado" for="estado" class="block text-sm mb-1 text-white/80"
							>Estado</label
						>
						<GlassSelect
							id="estado"
							ariaLabel="Seleccionar estado"
							ariaLabelledby="label-estado"
							items={estadoItems}
							value={newUser.active ? 'Activo' : 'Inactivo'}
							onChange={(v) => (newUser.active = v === 'Activo')}
						/>
					</div>

					{#if formErrors.general}
						<p class="text-red-400 text-sm">{formErrors.general}</p>
					{/if}

					<div class="flex justify-end gap-2 pt-2">
						<button type="button" onclick={closeModal} class="glass-button">Cancelar</button>
						<button
							type="submit"
							class="glass-button btn-success disabled:opacity-50"
							disabled={submitting}
						>
							{editingUser ? 'Guardar Cambios' : submitting ? 'Creando…' : 'Crear Usuario'}
						</button>
					</div>
				</form>
			</div>
		</div>
	{/if}
</div>

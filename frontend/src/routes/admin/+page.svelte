<script lang="ts">

	import { onMount } from 'svelte';
	import { apiFetch } from '$lib/api';
	import { showAlert, showConfirm } from '$lib/dialog';
	import PasswordNewConfirm from '$lib/components/PasswordNewConfirm.svelte';
	import GlassSelect from '$lib/components/GlassSelect.svelte';

	type Role = 'Admin' | 'Operador';

	interface User {
		id: number;
		nombre: string;
		email: string;
		rol: Role;
		estado: 'Activo' | 'Inactivo';
		username: string;
	}

	let users = $state<User[]>([]);
	let loadError = $state('');

	type BackendUser = {
		id: number;
		username: string;
		email: string;
		role: 'ROLE_ADMIN' | 'ROLE_OPERADOR';
		first_name: string;
		last_name: string;
		active: boolean;
	};

	const transformUser = (user: BackendUser): User => ({
		id: user.id,
		nombre: `${user.first_name} ${user.last_name}`.trim(),
		email: user.email,
		rol: user.role === 'ROLE_ADMIN' ? 'Admin' : 'Operador',
		estado: user.active ? 'Activo' : 'Inactivo',
		username: user.username
	});

	onMount(async () => {
		try {
			const res = await apiFetch('/admin/user');
			if (!res.ok) {
				console.error('Error al cargar usuarios:', await res.text());
				loadError = 'No se pudieron cargar los usuarios';
				return;
			}
			const data = (await res.json()) as { users: BackendUser[] };
			users = data.users.map((u) => transformUser(u));
		} catch (e) {
			console.error('Error de red al cargar usuarios', e);
			loadError = 'No se pudieron cargar los usuarios';
		}
	});

	const roleItems = [
		{ value: 'Admin' as Role, label: 'Admin' },
		{ value: 'Operador' as Role, label: 'Operador' }
	];
	const estadoItems = [
		{ value: 'Activo' as const, label: 'Activo' },
		{ value: 'Inactivo' as const, label: 'Inactivo' }
	];

	let searchQuery = $state('');

	const filteredUsers = $derived.by(() => {
		const q = searchQuery.trim().toLowerCase();
		if (!q) return users;
		return users.filter(
			(u) => u.nombre.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)
		);
	});

	let showModal = $state(false);
	let editingUser = $state<User | null>(null);
	let newUser = $state<{
		nombre: string;
		email: string;
		rol: Role;
		estado: 'Activo' | 'Inactivo';
		username: string;
		password: string;
		confirm_password: string;
	}>({
		nombre: '',
		email: '',
		rol: 'Operador',
		estado: 'Activo',
		username: '',
		password: '',
		confirm_password: ''
	});

	let formErrors = $state({
		nombre: '',
		email: '',
		username: '',
		password: '',
		confirm_password: '',
		general: ''
	});
	let submitting = $state(false);
	let toggling = $state<Record<number, boolean>>({});
	let deleting = $state<Record<number, boolean>>({});

	const openCreateModal = (): void => {
		editingUser = null;
		newUser = {
			nombre: '',
			email: '',
			rol: 'Operador',
			estado: 'Activo',
			username: '',
			password: '',
			confirm_password: ''
		};
		formErrors = {
			nombre: '',
			email: '',
			username: '',
			password: '',
			confirm_password: '',
			general: ''
		};
		showModal = true;
	}

	const openEditModal = (user: User): void => {
		editingUser = user;
		newUser = {
			nombre: user.nombre,
			email: user.email,
			rol: user.rol,
			estado: user.estado,
			username: user.username,
			password: '',
			confirm_password: ''
		};
		formErrors = {
			nombre: '',
			email: '',
			username: '',
			password: '',
			confirm_password: '',
			general: ''
		};
		showModal = true;
	}

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
	}

	const validate = (): boolean => {
		formErrors = {
			nombre: '',
			email: '',
			username: '',
			password: '',
			confirm_password: '',
			general: ''
		};
		let ok = true;
		if (!newUser.nombre?.trim()) {
			formErrors.nombre = 'Requerido';
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

	async function handleSubmit(event?: SubmitEvent) {
		if (event?.preventDefault) {
			event.preventDefault();
		}
		if (!validate()) {
			return;
		}
		submitting = true;
		try {
			const parts = (newUser.nombre ?? '').trim().split(/\s+/);
			const first_name = parts.shift() ?? '';
			const last_name = parts.join(' ');

			if (editingUser) {
				const updates: Record<string, unknown> = {};
				updates.first_name = first_name;
				updates.last_name = last_name;
				if (newUser.email !== editingUser.email) {
					updates.email = newUser.email;
				}
				if (newUser.rol !== editingUser.rol) {
					updates.role = newUser.rol === 'Admin' ? 'ROLE_ADMIN' : 'ROLE_OPERADOR';
				}
				if (Object.keys(updates).length > 0) {
					const resUpdate = await apiFetch(`/admin/user/${editingUser.id}`, {
						method: 'PATCH',
						body: JSON.stringify(updates)
					});
					if (!resUpdate.ok) {
						const err = await resUpdate.json().catch(() => ({}));
						formErrors.general = err?.detail ?? 'Error al actualizar usuario';
						return;
					}
					const data = await resUpdate.json();
					const updated = data.user as {
						id: number;
						username: string;
						email: string;
						role: 'ROLE_ADMIN' | 'ROLE_OPERADOR';
						first_name: string;
						last_name: string;
						active: boolean;
					};
					users = users.map((u) => (u.id === updated.id ? transformUser(updated) : u));
				}

				if (newUser.estado !== editingUser.estado) {
					const id = editingUser.id;
					const estado = newUser.estado;
					const action = estado === 'Activo' ? 'enable' : 'disable';
					const resEstado = await apiFetch(`/admin/user/${id}/${action}`, { method: 'PATCH' });
					if (!resEstado.ok) {
						const err = await resEstado.json().catch(() => ({}));
						formErrors.general = err?.detail ?? 'Error al cambiar el estado';
						return;
					}
					users = users.map((u) => (u.id === id ? { ...u, estado } : u));
				}

				if (newUser.password) {
					const resPwd = await apiFetch(`/admin/user/${editingUser.id}/reset-password`, {
						method: 'POST',
						body: JSON.stringify({
							new_password: newUser.password,
							confirm_password: newUser.confirm_password
						})
					});
					if (!resPwd.ok) {
						const err = await resPwd.json().catch(() => ({}));
						formErrors.general = err?.detail ?? 'Error al cambiar contraseña';
						return;
					}
				}

				showModal = false;
				return;
			}

			const payload = {
				username: newUser.username,
				password: newUser.password,
				confirm_password: newUser.confirm_password,
				email: newUser.email,
				role: newUser.rol === 'Admin' ? 'ROLE_ADMIN' : 'ROLE_OPERADOR',
				first_name,
				last_name,
				active: newUser.estado === 'Activo'
			};
			const res = await apiFetch('/admin/user-register', {
				method: 'POST',
				body: JSON.stringify(payload)
			});
			if (!res.ok) {
				const err = await res.json().catch(() => ({}));
				formErrors.general = err?.detail ?? 'Error al crear usuario';
				return;
			}
			const data = await res.json();
			const created = data.user as BackendUser;
			users = [...users, transformUser(created)];
			showModal = false;
		} catch (e) {
			formErrors.general = 'Error de red';
		} finally {
			submitting = false;
		}
	}

	async function toggleStatus(user: User): Promise<void> {
		if (toggling[user.id]) {
			return;
		}
		const prev = user.estado;
		const targetActive = prev !== 'Activo';
		toggling[user.id] = true;
		users = users.map((u) =>
			u.id === user.id ? { ...u, estado: targetActive ? 'Activo' : 'Inactivo' } : u
		);
		try {
			const path = targetActive
				? `/admin/user/${user.id}/enable`
				: `/admin/user/${user.id}/disable`;
			const res = await apiFetch(path, { method: 'PATCH' });
			if (!res.ok) {
				users = users.map((u) => (u.id === user.id ? { ...u, estado: prev } : u));
				const err = await res.json().catch(() => ({}) as any);
				await showAlert({
					message: err?.detail ?? 'No se pudo actualizar el estado',
					variant: 'danger'
				});
				return;
			}
			const data = await res.json().catch(() => null as any);
			const active = data?.user?.active;
			if (typeof active === 'boolean') {
				users = users.map((u) =>
					u.id === user.id ? { ...u, estado: active ? 'Activo' : 'Inactivo' } : u
				);
			}
		} catch (e) {
			users = users.map((u) => (u.id === user.id ? { ...u, estado: prev } : u));
			await showAlert({ message: 'Error de red al actualizar estado', variant: 'danger' });
		} finally {
			toggling[user.id] = false;
		}
	}

	async function deleteUser(userId: number): Promise<void> {
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
		if (!confirmed) return;
		deleting[userId] = true;
		const prev = users;
		users = users.filter((u) => u.id !== userId);
		try {
			const res = await apiFetch(`/admin/user/${userId}`, { method: 'DELETE' });
			if (!res.ok) {
				users = prev; // revert
				const err = await res.json().catch(() => ({}));
				await showAlert({
					message: err?.detail ?? 'No se pudo eliminar el usuario',
					variant: 'danger'
				});
				return;
			}
		} catch (e) {
			users = prev; // revert
			await showAlert({ message: 'Error de red al eliminar usuario', variant: 'danger' });
		} finally {
			deleting[userId] = false;
		}
	}
</script>

<svelte:window onkeydown={escapeClosesModal}/>

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
							{user.nombre}
						</td>
						<td class="p-3">
							{user.email}
						</td>
						<td class="p-3">
							<div class="flex items-center">
								<span
									class={`px-2 py-1 rounded text-xs font-medium border ${user.rol === 'Admin' ? 'text-purple-200 bg-purple-400/15 border-purple-300/30' : 'text-sky-200 bg-sky-400/15 border-sky-300/30'}`}
								>
									{user.rol}
								</span>
							</div>
						</td>
						<td class="p-3">
							<button
								onclick={() => toggleStatus(user)}
								aria-busy={toggling[user.id]}
								disabled={toggling[user.id]}
								class={`glass-button px-2 py-1 text-xs ${user.estado === 'Activo' ? 'btn-success' : 'btn-danger'} ${toggling[user.id] ? 'opacity-50 cursor-not-allowed' : ''}`}
							>
								{user.estado}
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
									onclick={() => deleteUser(user.id)}
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
					<div>
						<label for="nombre" class="block text-sm mb-1 text-white/80">Nombre completo</label>
						<input
							type="text"
							id="nombre"
							bind:value={newUser.nombre}
							class="glass-input"
							class:border-red-500={formErrors.nombre}
						/>
						{#if formErrors.nombre}
							<p class="text-red-400 text-xs mt-1">{formErrors.nombre}</p>
						{/if}
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
							value={newUser.rol}
							onChange={(v) => (newUser.rol = v as Role)}
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
							value={newUser.estado}
							onChange={(v) => (newUser.estado = v as 'Activo' | 'Inactivo')}
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

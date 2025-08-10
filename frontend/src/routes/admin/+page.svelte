<script lang="ts">
	import { onMount } from 'svelte';
	import { apiFetch } from '$lib/api';
	import { showAlert, showConfirm } from '$lib/dialog';
	import PasswordNewConfirm from '$lib/components/PasswordNewConfirm.svelte';

	// Tipos para los usuarios y roles
	type Role = 'Admin' | 'Operador';

	interface User {
		id: number;
		nombre: string;
		email: string;
		rol: Role;
		estado: 'Activo' | 'Inactivo';
		username: string;
	}

	// Estado para los usuarios (se cargan desde backend)
	let users = $state<User[]>([]);

	// Cargar usuarios reales desde la API al montar
	type BackendUser = {
		id: number;
		username: string;
		email: string;
		role: 'ROLE_ADMIN' | 'ROLE_OPERADOR';
		first_name: string;
		last_name: string;
		active: boolean;
	};

	onMount(async () => {
		try {
			const res = await apiFetch('/admin/user');
			if (!res.ok) {
				console.error('Error al cargar usuarios:', await res.text());
				return;
			}
			const data = (await res.json()) as { users: BackendUser[] };
			users = data.users.map((u) => ({
				id: u.id,
				nombre: `${u.first_name} ${u.last_name}`.trim(),
				email: u.email,
				rol: u.role === 'ROLE_ADMIN' ? 'Admin' : 'Operador',
				estado: u.active ? 'Activo' : 'Inactivo',
				username: u.username
			}));
		} catch (e) {
			console.error('Error de red al cargar usuarios', e);
		}
	});

	// Estado para el filtro de búsqueda
	let searchQuery = $state('');

	// Estado para el modal de edición/creación
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

	// Estado para mensajes de error en el formulario
	let formErrors = $state({
		nombre: '',
		email: '',
		username: '',
		password: '',
		confirm_password: '',
		general: ''
	});
	let submitting = $state(false);
	// Estado de carga por usuario al cambiar estado
	let toggling = $state<Record<number, boolean>>({});
	// Estado de eliminación por usuario
	let deleting = $state<Record<number, boolean>>({});

	// Función para abrir el modal de creación de usuario
	function openCreateModal(): void {
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

	// Función para abrir el modal de edición de usuario (solo UI local por ahora)
	function openEditModal(user: User): void {
		editingUser = user;
		// Para edición real habría que mapear a campos completos; mantenemos valores de muestra
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

	function closeModal(): void {
		if (submitting) return;
		showModal = false;
	}

	function validate(): boolean {
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
		if (!editingUser) {
			// Validaciones de creación (requerido + políticas básicas)
			if (!newUser.password) {
				formErrors.password = 'Requerido';
				ok = false;
			}
			if (!newUser.confirm_password) {
				formErrors.confirm_password = 'Requerido';
				ok = false;
			}
			if (newUser.password && newUser.password.length < 6) {
				formErrors.password = 'La contraseña debe tener al menos 6 caracteres';
				ok = false;
			}
			if (
				newUser.password &&
				(!/[A-Za-z]/.test(newUser.password) || !/\d/.test(newUser.password))
			) {
				formErrors.password = 'Debe incluir letras y números';
				ok = false;
			}
			if (
				newUser.password &&
				newUser.confirm_password &&
				newUser.password !== newUser.confirm_password
			) {
				formErrors.confirm_password = 'No coincide';
				ok = false;
			}
		} else {
			// En edición, validar contraseña solo si se quiere cambiar
			if (newUser.password || newUser.confirm_password) {
				if (!newUser.password) {
					formErrors.password = 'Requerido';
					ok = false;
				}
				if (!newUser.confirm_password) {
					formErrors.confirm_password = 'Requerido';
					ok = false;
				}
				if (newUser.password && newUser.password.length < 6) {
					formErrors.password = 'La contraseña debe tener al menos 6 caracteres';
					ok = false;
				}
				if (
					newUser.password &&
					(!/[A-Za-z]/.test(newUser.password) || !/\d/.test(newUser.password))
				) {
					formErrors.password = 'Debe incluir letras y números';
					ok = false;
				}
				if (
					newUser.password &&
					newUser.confirm_password &&
					newUser.password !== newUser.confirm_password
				) {
					formErrors.confirm_password = 'No coincide';
					ok = false;
				}
			}
		}
		return ok;
	}

	async function handleSubmit(event?: SubmitEvent) {
		// Prevent default submit in new event syntax
		if (event?.preventDefault) event.preventDefault();
		if (!validate()) return;
		submitting = true;
		try {
			// Separar nombre en first/last
			const parts = (newUser.nombre ?? '').trim().split(/\s+/);
			const first_name = parts.shift() ?? '';
			const last_name = parts.join(' ');

			if (editingUser) {
				// Actualización de datos del usuario
				const updates: Record<string, unknown> = {};
				// Enviar siempre nombres por simplicidad
				updates.first_name = first_name;
				updates.last_name = last_name;
				if (newUser.email !== editingUser.email) updates.email = newUser.email;
				if (newUser.rol !== editingUser.rol)
					updates.role = newUser.rol === 'Admin' ? 'ROLE_ADMIN' : 'ROLE_OPERADOR';

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
					users = users.map((u) =>
						u.id === updated.id
							? {
									id: updated.id,
									nombre: `${updated.first_name} ${updated.last_name}`.trim(),
									email: updated.email,
									rol: updated.role === 'ROLE_ADMIN' ? 'Admin' : 'Operador',
									estado: updated.active ? 'Activo' : 'Inactivo',
									username: updated.username
								}
							: u
					);
				}

				// Cambio de contraseña (opcional en edición)
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
					// 204 sin contenido esperado
				}

				showModal = false;
				return;
			}

			// Creación de usuario
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
			const created = data.user as {
				id: number;
				email: string;
				role: string;
				first_name: string;
				last_name: string;
				active: boolean;
				username: string;
			};
			// Actualizar lista local
			users = [
				...users,
				{
					id: created.id,
					nombre: `${created.first_name} ${created.last_name}`.trim(),
					email: created.email,
					rol: created.role === 'ROLE_ADMIN' ? 'Admin' : 'Operador',
					estado: created.active ? 'Activo' : 'Inactivo',
					username: created.username
				}
			];
			showModal = false;
		} catch (e) {
			formErrors.general = 'Error de red';
		} finally {
			submitting = false;
		}
	}

	// Funciones locales de UI
	function changeRole(user: User): void {
		const newRole: Role = user.rol === 'Admin' ? 'Operador' : 'Admin';
		users = users.map((u) => (u.id === user.id ? { ...u, rol: newRole } : u));
	}

	async function toggleStatus(user: User): Promise<void> {
		if (toggling[user.id]) return;
		const prev = user.estado;
		const targetActive = prev !== 'Activo';
		// Optimistic update
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
				// revert on error
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
		if (deleting[userId]) return;
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
		// Optimistic removal
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
			// 204 expected, nothing else
		} catch (e) {
			users = prev; // revert
			await showAlert({ message: 'Error de red al eliminar usuario', variant: 'danger' });
		} finally {
			deleting[userId] = false;
		}
	}
</script>

<div class="min-h-screen bg-[#1a1e2a] text-white">
	<!-- Header -->
	<header class="bg-[#1a1e2a] p-4 border-b border-gray-800 flex items-center justify-between">
		<div class="flex items-center">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-6 w-6 text-blue-400 mr-2"
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
			<h1 class="text-xl font-semibold">Administración de Usuarios</h1>
		</div>
		<button
			onclick={openCreateModal}
			class="bg-blue-600 hover:bg-blue-500 text-white py-2 px-4 rounded flex items-center"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-5 w-5 mr-1"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
			</svg>
			Nuevo Usuario
		</button>
	</header>

	<!-- Barra de filtro -->
	<div class="p-4">
		<div class="relative">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-5 w-5 absolute left-3 top-3 text-gray-400"
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
				class="w-full bg-[#2d3748] text-white pl-10 p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
			/>
		</div>
	</div>

	<!-- Tabla de usuarios -->
	<div class="overflow-x-auto px-4">
		<table class="w-full border-collapse">
			<!-- Encabezados de tabla -->
			<thead>
				<tr class="bg-[#2d3748] text-gray-300">
					<th class="p-3 text-left font-medium">ID</th>
					<th class="p-3 text-left font-medium">Nombre</th>
					<th class="p-3 text-left font-medium">Email</th>
					<th class="p-3 text-left font-medium">Rol</th>
					<th class="p-3 text-left font-medium">Estado</th>
					<th class="p-3 text-left font-medium">Acciones</th>
				</tr>
			</thead>
			<!-- Cuerpo de la tabla -->
			<tbody>
				{#each users.filter((u) => u.nombre
							.toLowerCase()
							.includes(searchQuery.toLowerCase()) || u.email
							.toLowerCase()
							.includes(searchQuery.toLowerCase())) as user}
					<tr class="border-b border-gray-700">
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
									class={`px-2 py-1 rounded text-xs font-medium ${
										user.rol === 'Admin'
											? 'bg-purple-900 text-purple-200'
											: 'bg-blue-900 text-blue-200'
									}`}
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
								class={`px-2 py-1 rounded text-xs font-medium ${
									user.estado === 'Activo'
										? 'bg-green-900 text-green-200'
										: 'bg-red-900 text-red-200'
								}
								${toggling[user.id] ? 'opacity-50 cursor-not-allowed' : ''}`}
							>
								{user.estado}
							</button>
						</td>
						<td class="p-3">
							<div class="flex gap-2">
								<button
									onclick={() => openEditModal(user)}
									class="bg-blue-600 hover:bg-blue-500 text-white text-sm py-1 px-3 rounded"
									title="Editar usuario"
								>
									Editar
								</button>
								<button
									onclick={() => deleteUser(user.id)}
									class="bg-red-600 hover:bg-red-500 text-white text-sm py-1 px-3 rounded disabled:opacity-50"
									title="Eliminar usuario"
									disabled={deleting[user.id]}
								>
									Eliminar
								</button>
							</div>
						</td>
					</tr>
				{/each}

				{#if users.length === 0}
					<tr>
						<td colspan="7" class="p-4 text-center text-gray-400">
							No se encontraron usuarios que coincidan con la búsqueda.
						</td>
					</tr>
				{/if}
			</tbody>
		</table>
	</div>

	<!-- Modal para crear/editar usuario -->
	{#if showModal}
		<div
			class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
			role="presentation"
			tabindex="-1"
			onclick={(e) => {
				// Cerrar al clickear fuera del modal
				if (e.target === e.currentTarget) closeModal();
			}}
			onkeydown={(e) => {
				// Permitir cerrar con Escape
				if (e.key === 'Escape') closeModal();
			}}
		>
			<div
				class="relative bg-[#1a202c] rounded-lg shadow-lg p-6 w-full max-w-md"
				role="dialog"
				aria-modal="true"
				tabindex="0"
				onclick={(e) => e.stopPropagation()}
				onkeydown={(e) => {
					// Permitir cerrar con Escape desde el dialog
					if (e.key === 'Escape') closeModal();
				}}
			>
				<button
					type="button"
					class="absolute top-3 right-3 text-gray-400 hover:text-white focus:outline-none focus:ring-2 focus:ring-gray-600 rounded"
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

				<h3 class="text-xl font-semibold mb-4">
					{editingUser ? 'Editar Usuario' : 'Nuevo Usuario'}
				</h3>

				<form class="space-y-4" onsubmit={handleSubmit}>
					<!-- Campo Nombre completo -->
					<div>
						<label for="nombre" class="block text-sm font-medium text-gray-400 mb-1"
							>Nombre completo</label
						>
						<input
							type="text"
							id="nombre"
							bind:value={newUser.nombre}
							class="w-full bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
							class:border-red-500={formErrors.nombre}
						/>
						{#if formErrors.nombre}
							<p class="text-red-500 text-xs mt-1">{formErrors.nombre}</p>
						{/if}
					</div>

					<!-- Campo Email -->
					<div>
						<label for="email" class="block text-sm font-medium text-gray-400 mb-1">Email</label>
						<input
							type="email"
							id="email"
							bind:value={newUser.email}
							class="w-full bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
							class:border-red-500={formErrors.email}
						/>
						{#if formErrors.email}
							<p class="text-red-500 text-xs mt-1">{formErrors.email}</p>
						{/if}
					</div>

					<!-- Campo Username -->
					<div>
						<label for="username" class="block text-sm font-medium text-gray-400 mb-1"
							>Usuario</label
						>
						<input
							type="text"
							id="username"
							bind:value={newUser.username}
							class="w-full bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
							class:border-red-500={formErrors.username}
						/>
						{#if formErrors.username}
							<p class="text-red-500 text-xs mt-1">{formErrors.username}</p>
						{/if}
					</div>

					<!-- Password + Confirm reutilizando componente con barra de fuerza -->
					<PasswordNewConfirm
						bind:newPassword={newUser.password}
						bind:confirmPassword={newUser.confirm_password}
						errorNew={formErrors.password}
						errorConfirm={formErrors.confirm_password}
					/>

					<!-- Campo Rol -->
					<div>
						<label for="rol" class="block text-sm font-medium text-gray-400 mb-1">Rol</label>
						<select
							id="rol"
							bind:value={newUser.rol}
							class="w-full bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
						>
							<option value="Admin">Admin</option>
							<option value="Operador">Operador</option>
						</select>
					</div>

					<!-- Campo Estado -->
					<div>
						<label for="estado" class="block text-sm font-medium text-gray-400 mb-1">Estado</label>
						<select
							id="estado"
							bind:value={newUser.estado}
							class="w-full bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
						>
							<option value="Activo">Activo</option>
							<option value="Inactivo">Inactivo</option>
						</select>
					</div>

					{#if formErrors.general}
						<p class="text-red-500 text-sm">{formErrors.general}</p>
					{/if}

					<!-- Botones de acción -->
					<div class="flex justify-end gap-3 mt-6">
						<button
							type="button"
							onclick={closeModal}
							class="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded"
							aria-disabled={submitting}
						>
							Cancelar
						</button>
						<button
							type="submit"
							class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded disabled:opacity-50"
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

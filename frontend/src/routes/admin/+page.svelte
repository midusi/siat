<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import Modal from '$lib/components/Modal.svelte';
	import SearchInput from '$lib/components/SearchInput.svelte';
	import { onMount } from 'svelte';
	import { showAlert, showConfirm } from '$lib/dialog';
	import type { User } from '$lib/types/user';
	import UserEditForm from './UserEditForm.svelte';
	import UserTable from './UserTable.svelte';
	import {
		ApiError,
		changeUserStatus,
		createUser,
		deleteUser,
		fetchUsers,
		updateUser,
		type UserUpdates
	} from '$lib/services/users';

	import {
		emptyErrors,
		hasErrors,
		validateUserForm,
		type FormErrors,
		type UserForm
	} from '$lib/validation/user';

	const emptyForm = (): UserForm => ({
		first_name: '',
		last_name: '',
		email: '',
		username: '',
		role: 'ROLE_OPERADOR',
		active: true,
		password: '',
		confirm_password: ''
	});

	const formFromUser = (user: User): UserForm => ({
		first_name: user.first_name,
		last_name: user.last_name,
		email: user.email,
		username: user.username,
		role: user.role,
		active: user.active,
		password: '',
		confirm_password: ''
	});

	let users = $state<User[]>([]);
	let loadError = $state('');
	let searchQuery = $state('');
	let showModal = $state(false);
	let editingUser = $state<User | null>(null);
	let newUser = $state<UserForm>(emptyForm());
	let formErrors = $state<FormErrors>(emptyErrors());
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

	const patchUser = (id: number, patch: Partial<User>): void => {
		users = users.map((u) => (u.id === id ? { ...u, ...patch } : u));
	};

	const openCreateModal = (): void => {
		editingUser = null;
		newUser = emptyForm();
		formErrors = emptyErrors();
		showModal = true;
	};

	const openEditModal = (user: User): void => {
		editingUser = user;
		newUser = formFromUser(user);
		formErrors = emptyErrors();
		showModal = true;
	};

	const closeModal = (): void => {
		if (submitting) {
			return;
		}
		showModal = false;
	};

	const handleSubmit = async (event?: SubmitEvent) => {
		if (event?.preventDefault) {
			event.preventDefault();
		}
		formErrors = validateUserForm(newUser, !!editingUser);
		if (hasErrors(formErrors)) {
			return;
		}
		submitting = true;
		try {
			if (editingUser) {
				const current = editingUser;
				const updates: UserUpdates = {};
				const fields = ['first_name', 'last_name', 'email', 'role', 'active'] as const;
				for (const field of fields) {
					if (newUser[field] !== current[field]) {
						Object.assign(updates, { [field]: newUser[field] });
					}
				}
				if (newUser.password) {
					updates.password = newUser.password;
					updates.confirm_password = newUser.confirm_password;
				}

				if (Object.keys(updates).length > 0) {
					const updated = await updateUser(current.id, updates);
					patchUser(updated.id, updated);
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
			const message = e instanceof Error ? e.message : 'Error de red';
			const field = e instanceof ApiError ? e.field : undefined;
			if (field && field !== 'general' && field in formErrors) {
				formErrors[field as keyof FormErrors] = message;
			} else {
				formErrors.general = message;
			}
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
		patchUser(user.id, { active: targetActive });
		try {
			const updated = await changeUserStatus(user.id, targetActive);
			if (updated) {
				patchUser(user.id, updated);
			}
		} catch (e) {
			patchUser(user.id, { active: prev });
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
			await showAlert({
				message: e instanceof Error ? e.message : 'Error de red al eliminar usuario',
				variant: 'danger'
			});
		} finally {
			deleting[userId] = false;
		}
	};
</script>

<div class="page-container">
	<div class="mb-6 flex items-center justify-between">
		<div class="flex items-center gap-2">
			<Icon name="sliders" class="h-5 w-5 text-amber-300" />
			<h1 class="heading-1">Administración de Usuarios</h1>
		</div>
		<button onclick={openCreateModal} class="glass-button btn-success px-3 py-2">
			<Icon name="plus" class="h-4 w-4 mr-1" />
			Nuevo Usuario
		</button>
	</div>

	<div class="mb-4">
		<SearchInput bind:value={searchQuery} placeholder="Buscar usuarios por nombre o email..." />
	</div>

	<UserTable
		users={filteredUsers}
		{toggling}
		{deleting}
		{loadError}
		isFiltering={!!searchQuery.trim()}
		onedit={openEditModal}
		ontoggle={toggleStatus}
		ondelete={removeUser}
	/>

	<Modal
		open={showModal}
		title={editingUser ? 'Editar Usuario' : 'Nuevo Usuario'}
		onclose={closeModal}
	>
		<UserEditForm
			bind:form={newUser}
			errors={formErrors}
			isEditing={!!editingUser}
			{submitting}
			onsubmit={handleSubmit}
			oncancel={closeModal}
		/>
	</Modal>
</div>

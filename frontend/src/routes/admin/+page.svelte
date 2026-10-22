<script lang="ts">
	import { ApiError } from '$lib/services/errors';
	import {
		changeUserStatus,
		createUser,
		deleteUser,
		fetchUsers,
		updateUser
	} from '$lib/services/users';
	import { emptyErrors, hasErrors, validateUserForm } from '$lib/validation/user';
	import Icon from '$lib/components/Icon.svelte';
	import Modal from '$lib/components/Modal.svelte';
	import { onMount } from 'svelte';
	import SearchInput from '$lib/components/SearchInput.svelte';
	import { showAlert, showConfirm } from '$lib/dialog';
	import UserEditForm from './UserEditForm.svelte';
	import UserTable from './UserTable.svelte';

	import type { FormErrors, UserForm } from '$lib/validation/user';
	import type { PendingByUserId, User } from '$lib/types/user';
	import type { UserUpdates } from '$lib/services/users';

	type EditableField = 'active' | 'email' | 'first_name' | 'last_name' | 'role';

	const DELETE_MESSAGE: string =
		'¿Estás seguro de que deseas eliminar este usuario? Esta acción no se puede deshacer.';
	const EDITABLE_FIELDS: Array<EditableField> = [
		'active',
		'email',
		'first_name',
		'last_name',
		'role'
	];
	const EMPTY_FORM: UserForm = {
		active: true,
		confirm_password: '',
		email: '',
		first_name: '',
		last_name: '',
		password: '',
		role: 'ROLE_OPERADOR',
		username: ''
	};

	let deleting: PendingByUserId = $state({});
	let editingUser: User | null = $state(null);
	let formErrors: FormErrors = $state(emptyErrors());
	let loadError: string = $state('');
	let newUser: UserForm = $state({ ...EMPTY_FORM });
	let searchQuery: string = $state('');
	let showModal: boolean = $state(false);
	let submitting: boolean = $state(false);
	let toggling: PendingByUserId = $state({});
	let users: Array<User> = $state([]);

	const filteredUsers: Array<User> = $derived.by(() => {
		const q: string = searchQuery.trim().toLowerCase();
		if (!q) {
			return users;
		}
		return users.filter(
			(u) =>
				`${u.first_name} ${u.last_name}`.toLowerCase().includes(q) ||
				u.email.toLowerCase().includes(q)
		);
	});

	onMount(async () => {
		try {
			users = await fetchUsers();
		} catch (e) {
			console.error('Error de red al cargar usuarios', e);
			loadError = 'No se pudieron cargar los usuarios';
		}
	});

	const formFromUser = (user: User): UserForm => ({
		active: user.active,
		confirm_password: '',
		email: user.email,
		first_name: user.first_name,
		last_name: user.last_name,
		password: '',
		role: user.role,
		username: user.username
	});

	const patchUser = (id: number, patch: Partial<User>): void => {
		users = users.map((u) => (u.id === id ? { ...u, ...patch } : u));
	};

	const openCreateModal = (): void => {
		editingUser = null;
		newUser = { ...EMPTY_FORM };
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

	const buildUpdates = (current: User): UserUpdates => {
		const updates: UserUpdates = {};
		for (const field of EDITABLE_FIELDS) {
			if (newUser[field] !== current[field]) {
				Object.assign(updates, { [field]: newUser[field] });
			}
		}
		if (newUser.password) {
			updates.password = newUser.password;
			updates.confirm_password = newUser.confirm_password;
		}
		return updates;
	};

	const handleSubmit = async (event: SubmitEvent): Promise<void> => {
		event.preventDefault();
		formErrors = validateUserForm(newUser, !!editingUser);
		if (hasErrors(formErrors)) {
			return;
		}
		submitting = true;
		try {
			if (editingUser) {
				const updates: UserUpdates = buildUpdates(editingUser);
				if (Object.keys(updates).length > 0) {
					const updated: User = await updateUser(editingUser.id, updates);
					patchUser(updated.id, updated);
				}
			} else {
				const created: User = await createUser(newUser);
				users = [...users, created];
			}
			showModal = false;
		} catch (e) {
			const message: string = e instanceof Error ? e.message : 'Error de red';
			const field: string | undefined = e instanceof ApiError ? e.field : undefined;
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
		const prev: boolean = user.active;
		toggling[user.id] = true;
		patchUser(user.id, { active: !prev });
		try {
			const updated: User | null = await changeUserStatus(user.id, !prev);
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
		const confirmed: boolean = await showConfirm({
			message: DELETE_MESSAGE,
			variant: 'danger',
			confirmText: 'Eliminar',
			cancelText: 'Cancelar'
		});
		if (!confirmed) {
			return;
		}
		deleting[userId] = true;
		const prev: Array<User> = users;
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

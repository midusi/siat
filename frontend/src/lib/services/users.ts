import { apiError } from './errors';
import { apiFetch } from '$lib/api';

import type { NewUser, User } from '$lib/types/user';

export type UserUpdates = Partial<
	Pick<User, 'email' | 'role' | 'first_name' | 'last_name' | 'active'>
> & {
	password?: string;
	confirm_password?: string;
};

type UserResponse = { user: User };
type UsersResponse = { users: Array<User> };

const ADMIN_USER_API: string = '/admin/user';

export const fetchUsers = async (): Promise<Array<User>> => {
	const res: Response = await apiFetch(ADMIN_USER_API);
	if (!res.ok) {
		throw await apiError(res, 'No se pudieron cargar los usuarios');
	}
	const data: UsersResponse = (await res.json()) as UsersResponse;
	return data.users;
};

export const createUser = async (payload: NewUser): Promise<User> => {
	const res: Response = await apiFetch(`${ADMIN_USER_API}-register`, {
		method: 'POST',
		body: JSON.stringify(payload)
	});
	if (!res.ok) {
		throw await apiError(res, 'Error al crear usuario');
	}
	const data: UserResponse = (await res.json()) as UserResponse;
	return data.user;
};

export const updateUser = async (id: number, updates: UserUpdates): Promise<User> => {
	const res: Response = await apiFetch(`${ADMIN_USER_API}/${id}`, {
		method: 'PATCH',
		body: JSON.stringify(updates)
	});
	if (!res.ok) {
		throw await apiError(res, 'Error al actualizar usuario');
	}
	const data: UserResponse = (await res.json()) as UserResponse;
	return data.user;
};

export const deleteUser = async (id: number): Promise<void> => {
	const res: Response = await apiFetch(`${ADMIN_USER_API}/${id}`, { method: 'DELETE' });
	if (!res.ok) {
		throw await apiError(res, 'Error al eliminar el usuario');
	}
};

export const changeUserStatus = async (id: number, wantedStatus: boolean): Promise<User | null> => {
	const action: string = wantedStatus ? 'enable' : 'disable';
	const res: Response = await apiFetch(`${ADMIN_USER_API}/${id}/${action}`, { method: 'PATCH' });
	if (!res.ok) {
		throw await apiError(res, 'No se pudo cambiar el estado del usuario');
	}
	const data: UserResponse | null = await res.json().catch((): null => null);
	return data?.user ?? null;
};

export const resetUserPassword = async (
	id: number,
	new_password: string,
	confirm_password: string
): Promise<void> => {
	const res: Response = await apiFetch(`${ADMIN_USER_API}/${id}/reset-password`, {
		method: 'POST',
		body: JSON.stringify({ new_password, confirm_password })
	});
	if (!res.ok) {
		throw await apiError(res, 'No se pudo cambiar la contraseña del usuario');
	}
};

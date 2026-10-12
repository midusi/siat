import { apiFetch } from '$lib/api';
import type { Role, User } from '$lib/types/user';
import { apiError } from './errors';

const ADMIN_USER_API: string = '/admin/user';

export const fetchUsers = async (): Promise<User[]> => {
    const res = await apiFetch(ADMIN_USER_API);
    if (!res.ok) {
        throw await apiError(res, 'No se pudieron cargar los usuarios');
    }
    const data = (await res.json()) as { users: User[] };
    return data.users;
}

export const createUser = async (payload: {
    username: string,
    password: string,
    confirm_password: string,
    email: string,
    role: Role,
    first_name: string,
    last_name: string,
    active: boolean
}): Promise<User> => {
    const res = await apiFetch(`${ADMIN_USER_API}-register`, {
        method: 'POST',
        body: JSON.stringify(payload)
    });
    if (!res.ok) {
        throw await apiError(res, 'Error al crear usuario');
    }
    const data = await res.json();
    return data.user as User;
}

export type UserUpdates = Partial<
    Pick<User, 'email' | 'role' | 'first_name' | 'last_name' | 'active'>
> & {
    password?: string;
    confirm_password?: string;
};

export const updateUser = async (id: number, updates: UserUpdates): Promise<User> => {
    const res = await apiFetch(`${ADMIN_USER_API}/${id}`, { method: 'PATCH', body: JSON.stringify(updates) });
    if (!res.ok) {
        throw await apiError(res, 'Error al actualizar usuario');
    }
    const data = await res.json();
    return data.user as User;
}

export const deleteUser = async (id: number): Promise<void> => {
    const res = await apiFetch(`${ADMIN_USER_API}/${id}`, { method: 'DELETE' });
    if (!res.ok) {
        throw await apiError(res, 'Error al eliminar el usuario');
    }
}

export const changeUserStatus = async (id: number, wantedStatus: boolean): Promise<User | null> => {
    const action = wantedStatus ? 'enable' : 'disable';
    const res = await apiFetch(`${ADMIN_USER_API}/${id}/${action}`, { method: 'PATCH' });
    if (!res.ok) {
        throw await apiError(res, 'No se pudo cambiar el estado del usuario');
    }
    const data = await res.json().catch(() => null);
    return (data?.user as User) ?? null;
}

export const resetUserPassword = async (id: number, new_password: string, confirm_password: string): Promise<void> => {
    const res = await apiFetch(`${ADMIN_USER_API}/${id}/reset-password`, { method: 'POST', body: JSON.stringify({ new_password, confirm_password }) });
    if (!res.ok) {
        throw await apiError(res, 'No se pudo cambiar la contraseña del usuario');
    }
}
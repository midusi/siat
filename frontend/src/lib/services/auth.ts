import { apiFetch } from '$lib/api';
import { apiError } from './errors';

const AUTH_API: string = '/auth/';

export const login = async (username: string, password: string): Promise<void> => {
    const res = await apiFetch(`${AUTH_API}login`, {
        method: 'POST',
        body: JSON.stringify({ username, password })
    });

    if (!res.ok) {
        throw await apiError(res, 'Error de autenticación');
    }
}

export const logout = async () => {
    await apiFetch(`${AUTH_API}logout`, { method: 'POST' });
}
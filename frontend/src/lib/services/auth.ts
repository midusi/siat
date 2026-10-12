import { apiFetch } from '$lib/api';
import { apiError } from './errors';

export const login = async (username: string, password: string): Promise<void> => {
    const res = await apiFetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password })
    });

    if (!res.ok) {
        throw await apiError(res, 'Error de autenticación');
    }
}
import { apiError } from './errors';
import { apiFetch } from '$lib/api';

const AUTH_API: string = '/auth';

export const login = async (username: string, password: string): Promise<void> => {
	const res: Response = await apiFetch(`${AUTH_API}/login`, {
		method: 'POST',
		body: JSON.stringify({ username, password })
	});
	if (!res.ok) {
		throw await apiError(res, 'Error de autenticación');
	}
};

export const logout = async (): Promise<void> => {
	await apiFetch(`${AUTH_API}/logout`, { method: 'POST' });
};

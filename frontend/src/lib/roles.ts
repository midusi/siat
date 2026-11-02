import type { Role } from '$lib/types/user';

export const ROLE_LABELS: Record<Role, string> = {
	ROLE_ADMIN: 'Admin',
	ROLE_OPERADOR: 'Operador'
};

export const isAdmin = (role: Role | null | undefined): boolean => role === 'ROLE_ADMIN';

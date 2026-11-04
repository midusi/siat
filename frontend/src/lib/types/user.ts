export type Role = 'ROLE_ADMIN' | 'ROLE_OPERADOR';

export type User = {
	id: number;
	username: string;
	email: string;
	role: Role;
	first_name: string;
	last_name: string;
	active: boolean;
};

export type NewUser = Omit<User, 'id'> & {
	password: string;
	confirm_password: string;
};

export type PendingByUserId = Record<number, boolean>;

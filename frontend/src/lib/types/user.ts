export type Role = 'ROLE_ADMIN' | 'ROLE_OPERADOR';

export interface User {
    id: number;
    username: string;
    email: string;
    role: Role;
    first_name: string;
    last_name: string;
    active: boolean;
};
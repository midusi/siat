import type { User } from '$lib/types/user';

export type UserForm = Omit<User, 'id'> & { password: string; confirm_password: string };

export type FormErrors = {
	first_name: string;
	last_name: string;
	email: string;
	username: string;
	password: string;
	confirm_password: string;
	general: string;
};

export const emptyErrors = (): FormErrors => ({
	first_name: '',
	last_name: '',
	email: '',
	username: '',
	password: '',
	confirm_password: '',
	general: ''
});

export const hasErrors = (errors: Record<string, string>): boolean => Object.values(errors).some(Boolean);

export const validatePassword = (pwd: string): string => {
	if (pwd.length < 6) {
		return 'La contraseña debe tener al menos 6 caracteres';
	}
	if (!/[A-Za-z]/.test(pwd) || !/\d/.test(pwd)) {
		return 'Debe incluir letras y números';
	}
	return '';
};

export const validateUserForm = (form: UserForm, isEditing: boolean): FormErrors => {
	const errors = emptyErrors();

	if (!form.first_name?.trim()) {
		errors.first_name = 'Requerido';
	}
	if (!form.last_name?.trim()) {
		errors.last_name = 'Requerido';
	}
	if (!form.email?.trim()) {
		errors.email = 'Requerido';
	}
	if (!form.username?.trim()) {
		errors.username = 'Requerido';
	}

	const shouldValidatePassword = !isEditing || form.password || form.confirm_password;
	if (shouldValidatePassword) {
		const pwd = form.password;
		if (!pwd) {
			errors.password = 'Requerido';
		}
		if (!form.confirm_password) {
			errors.confirm_password = 'Requerido';
		}
		if (pwd) {
			errors.password = validatePassword(pwd);
		}
		if (pwd && form.confirm_password && pwd !== form.confirm_password) {
			errors.confirm_password = 'Las contraseñas no coinciden';
		}
	}

	return errors;
};

export type ChangePasswordErrors = {
	current: string;
	new: string;
	confirm: string;
	general: string;
};

export const emptyChangePasswordErrors = (): ChangePasswordErrors => ({
	current: '',
	new: '',
	confirm: '',
	general: ''
});

export const validateChangePassword = (
	current: string,
	pwd: string,
	confirm: string
): ChangePasswordErrors => {
	const errors = emptyChangePasswordErrors();

	if (!current) {
		errors.current = 'Ingresá tu contraseña actual';
	}
	errors.new = pwd ? validatePassword(pwd) : 'Ingresá la nueva contraseña';
	if (!confirm) {
		errors.confirm = 'Confirmá la nueva contraseña';
	} else if (pwd && pwd !== confirm) {
		errors.confirm = 'Las contraseñas no coinciden';
	}

	return errors;
};

import type { NewUser } from '$lib/types/user';

export type UserForm = NewUser;

export type FormErrors = {
	first_name: string;
	last_name: string;
	email: string;
	username: string;
	password: string;
	confirm_password: string;
	general: string;
};

export type ChangePasswordErrors = {
	current: string;
	new: string;
	confirm: string;
	general: string;
};

const MIN_PASSWORD_LENGTH: number = 6;
const REQUIRED_MESSAGE: string = 'Requerido';
const PASSWORD_MISMATCH_MESSAGE: string = 'Las contraseñas no coinciden';

const required = (value: string): string => (value.trim() ? '' : REQUIRED_MESSAGE);

export const validatePassword = (pwd: string): string => {
	if (pwd.length < MIN_PASSWORD_LENGTH) {
		return `La contraseña debe tener al menos ${MIN_PASSWORD_LENGTH} caracteres`;
	}
	if (!/[A-Za-z]/.test(pwd) || !/\d/.test(pwd)) {
		return 'Debe incluir letras y números';
	}
	return '';
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

export const validateUserForm = (form: UserForm, isEditing: boolean): FormErrors => {
	const errors: FormErrors = emptyErrors();

	errors.first_name = required(form.first_name);
	errors.last_name = required(form.last_name);
	errors.email = required(form.email);
	errors.username = required(form.username);

	const shouldValidatePassword: boolean =
		!isEditing || form.password !== '' || form.confirm_password !== '';
	if (shouldValidatePassword) {
		const pwd: string = form.password;
		errors.password = pwd ? validatePassword(pwd) : REQUIRED_MESSAGE;
		if (!form.confirm_password) {
			errors.confirm_password = REQUIRED_MESSAGE;
		} else if (pwd && pwd !== form.confirm_password) {
			errors.confirm_password = PASSWORD_MISMATCH_MESSAGE;
		}
	}

	return errors;
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
	const errors: ChangePasswordErrors = emptyChangePasswordErrors();

	if (!current) {
		errors.current = 'Ingresá tu contraseña actual';
	}
	errors.new = pwd ? validatePassword(pwd) : 'Ingresá la nueva contraseña';
	if (!confirm) {
		errors.confirm = 'Confirmá la nueva contraseña';
	} else if (pwd && pwd !== confirm) {
		errors.confirm = PASSWORD_MISMATCH_MESSAGE;
	}

	return errors;
};

export const hasErrors = (errors: Record<string, string>): boolean =>
	Object.values(errors).some(Boolean);

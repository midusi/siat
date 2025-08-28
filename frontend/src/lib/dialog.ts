import { writable } from 'svelte/store';

export type DialogVariant = 'default' | 'success' | 'danger' | 'warning' | 'info';

type BaseDialog = {
	title?: string;
	message: string;
	confirmText?: string;
	cancelText?: string;
	variant?: DialogVariant;
};

export type AlertDialogState = BaseDialog & {
	type: 'alert';
	resolve: () => void;
};

export type ConfirmDialogState = BaseDialog & {
	type: 'confirm';
	resolve: (val: boolean) => void;
};

export type DialogState = AlertDialogState | ConfirmDialogState;

export const dialogStore = writable<DialogState | null>(null);

export function showAlert(
	opts: Omit<Partial<AlertDialogState>, 'type' | 'resolve'> & { message: string }
): Promise<void> {
	return new Promise<void>((resolve) => {
		dialogStore.set({
			type: 'alert',
			title: opts.title,
			message: opts.message,
			confirmText: opts.confirmText ?? 'Aceptar',
			variant: opts.variant ?? 'default',
			resolve
		});
	});
}

export function showConfirm(
	opts: Omit<Partial<ConfirmDialogState>, 'type' | 'resolve'> & { message: string }
): Promise<boolean> {
	return new Promise<boolean>((resolve) => {
		dialogStore.set({
			type: 'confirm',
			title: opts.title,
			message: opts.message,
			confirmText: opts.confirmText ?? 'Confirmar',
			cancelText: opts.cancelText ?? 'Cancelar',
			variant: opts.variant ?? 'default',
			resolve
		});
	});
}

export function closeDialog(): void {
	dialogStore.set(null);
}

import type { Variant } from '$lib/types/variant';

type BaseDialog = {
	title?: string;
	message: string;
	confirmText: string;
	variant: Variant;
};

export type AlertDialogState = BaseDialog & {
	type: 'alert';
	resolve: () => void;
};

export type ConfirmDialogState = BaseDialog & {
	type: 'confirm';
	cancelText: string;
	resolve: (confirmed: boolean) => void;
};

export type DialogState = AlertDialogState | ConfirmDialogState;

type AlertOptions = {
	title?: string;
	message: string;
	confirmText?: string;
	variant?: Variant;
};

type ConfirmOptions = AlertOptions & {
	cancelText?: string;
};

type DialogStore = {
	readonly current: DialogState | null;
	open: (dialog: DialogState) => void;
	close: (confirmed: boolean) => void;
};

const DEFAULT_VARIANT: Variant = 'default';

const createDialogStore = (): DialogStore => {
	let current: DialogState | null = $state.raw(null);

	const close = (confirmed: boolean): void => {
		if (!current) {
			return;
		}
		const closing: DialogState = current;
		current = null;
		if (closing.type === 'alert') {
			closing.resolve();
		} else {
			closing.resolve(confirmed);
		}
	};

	const open = (dialog: DialogState): void => {
		close(false);
		current = dialog;
	};

	return {
		get current(): DialogState | null {
			return current;
		},
		open,
		close
	};
};

export const dialog: DialogStore = createDialogStore();

export const showAlert = (options: AlertOptions): Promise<void> =>
	new Promise<void>((resolve: () => void): void => {
		dialog.open({
			type: 'alert',
			title: options.title,
			message: options.message,
			confirmText: options.confirmText ?? 'Aceptar',
			variant: options.variant ?? DEFAULT_VARIANT,
			resolve
		});
	});

export const showConfirm = (options: ConfirmOptions): Promise<boolean> =>
	new Promise<boolean>((resolve: (confirmed: boolean) => void): void => {
		dialog.open({
			type: 'confirm',
			title: options.title,
			message: options.message,
			confirmText: options.confirmText ?? 'Confirmar',
			cancelText: options.cancelText ?? 'Cancelar',
			variant: options.variant ?? DEFAULT_VARIANT,
			resolve
		});
	});

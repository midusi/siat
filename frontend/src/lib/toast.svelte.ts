import type { Variant } from '$lib/types/variant';

export type Toast = {
	id: number;
	duration: number;
	message: string;
	variant: Variant;
};

type ToastOptions = {
	duration?: number;
	message: string;
	variant?: Variant;
};

type ToastStore = {
	readonly list: Array<Toast>;
	showToast: (opts: ToastOptions) => number;
	dismissToast: (id: number) => void;
};

const DEFAULT_DURATION: number = 3000;
const DEFAULT_VARIANT: Variant = 'info';

let nextId: number = 0;

const createToastStore = (): ToastStore => {
	let list: Array<Toast> = $state([]);

	const showToast = (opts: ToastOptions): number => {
		const id: number = nextId++;
		const toast: Toast = {
			id,
			duration: opts.duration ?? DEFAULT_DURATION,
			message: opts.message,
			variant: opts.variant ?? DEFAULT_VARIANT
		};
		list.push(toast);
		return id;
	};

	const dismissToast = (id: number): void => {
		list = list.filter((t: Toast): boolean => t.id !== id);
	};

	return {
		get list(): Array<Toast> {
			return list;
		},
		showToast,
		dismissToast
	};
};

export const toasts: ToastStore = createToastStore();

export const showSuccess = (message: string, duration?: number) => {
	return toasts.showToast({ message, duration, variant: 'success' });
}
export const showError = (message: string, duration?: number) => {
	return toasts.showToast({ message, duration, variant: 'danger' });
}
export const showInfo = (message: string, duration?: number) => {
	return toasts.showToast({ message, duration, variant: 'info' });
}
export const showWarning = (message: string, duration?: number) => {
	return toasts.showToast({ message, duration, variant: 'warning' });
}

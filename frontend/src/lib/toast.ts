import { writable } from 'svelte/store';

export type ToastVariant = 'default' | 'success' | 'danger' | 'warning' | 'info';

export type Toast = {
	id: number;
	message: string;
	variant: ToastVariant;
	duration: number; // ms
};

function createToastStore() {
	const { subscribe, update } = writable<Toast[]>([]);

	function showToast(opts: { message: string; variant?: ToastVariant; duration?: number }): number {
		const id = Date.now() + Math.floor(Math.random() * 1000);
		const toast: Toast = {
			id,
			message: opts.message,
			variant: opts.variant ?? 'info',
			duration: opts.duration ?? 3000
		};
		update((list) => [...list, toast]);
		return id;
	}

	function dismissToast(id: number) {
		update((list) => list.filter((t) => t.id !== id));
	}

	return {
		subscribe,
		showToast,
		dismissToast
	};
}

export const toasts = createToastStore();

// Helper shortcuts
export function showSuccess(message: string, duration?: number) {
	return toasts.showToast({ message, duration, variant: 'success' });
}
export function showError(message: string, duration?: number) {
	return toasts.showToast({ message, duration, variant: 'danger' });
}
export function showInfo(message: string, duration?: number) {
	return toasts.showToast({ message, duration, variant: 'info' });
}
export function showWarning(message: string, duration?: number) {
	return toasts.showToast({ message, duration, variant: 'warning' });
}

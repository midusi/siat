import type { Action } from 'svelte/action';

export const portal: Action<HTMLElement> = (node: HTMLElement): { destroy: () => void } => {
	document.body.appendChild(node);
	return {
		destroy: (): void => node.remove()
	};
};

import type { Action, ActionReturn } from 'svelte/action';

export const portal: Action<HTMLElement> = (node: HTMLElement): ActionReturn => {
	document.body.appendChild(node);
	return {
		destroy: (): void => node.remove()
	};
};

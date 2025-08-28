// Simple Svelte action to portal an element to target (default: document.body)
// Usage: <div use:portal>...</div> or <div use:portal={selectorOrElement}>...</div>
export function portal(node: HTMLElement, target: HTMLElement | string = 'body') {
	if (typeof window === 'undefined') return {} as any;
	const targetEl =
		typeof target === 'string' ? (document.querySelector(target) as HTMLElement | null) : target;
	if (!targetEl) return {} as any;
	targetEl.appendChild(node);
	return {
		destroy() {
			try {
				node.remove();
			} catch {}
		}
	};
}

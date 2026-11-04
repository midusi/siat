<script lang="ts">
	import './ScrollArea.css';

	import type { HTMLAttributes } from 'svelte/elements';
	import type { Snippet } from 'svelte';

	type Props = HTMLAttributes<HTMLDivElement> & {
		autoHide?: boolean;
		children: Snippet;
		class?: string;
		orientation?: 'y' | 'x' | 'both';
	};

	let {
		autoHide = false,
		children,
		class: className = '',
		orientation = 'y',
		...rest
	}: Props = $props();
</script>

<div {...rest} class={['scroll-area', orientation, autoHide && 'auto-hide', className]}>
	{@render children()}
</div>

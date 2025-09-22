<script lang="ts">
	// Reusable scroll area with themed scrollbar styles
	export let orientation: 'y' | 'x' | 'both' = 'y';
	export let className: string = '';
	// Optional: auto-hide thumb until hover
	export let autoHide: boolean = false;
	// Allow light customization via CSS vars if desired
	export let style: string = '';

	$: orientationClass = orientation === 'both' ? 'both' : orientation;
</script>

<div class={`scroll-area ${orientationClass} ${autoHide ? 'auto-hide' : ''} ${className}`} {style}>
	<slot />
</div>

<style>
	.scroll-area {
		/* Firefox scrollbar colors */
		scrollbar-width: thin; /* auto | thin | none */
		scrollbar-color: var(--sa-thumb, rgba(255, 255, 255, 0.35))
			var(--sa-track, rgba(255, 255, 255, 0.08));
		/* Make sure children can grow inside and this area scrolls */
		min-height: 0;
	}
	.scroll-area.y {
		overflow-y: auto;
		overflow-x: hidden;
	}
	.scroll-area.x {
		overflow-x: auto;
		overflow-y: hidden;
	}
	.scroll-area.both {
		overflow: auto;
	}

	/* WebKit-based browsers */
	.scroll-area::-webkit-scrollbar {
		width: var(--sa-size, 8px);
		height: var(--sa-size, 8px);
	}
	.scroll-area::-webkit-scrollbar-track {
		background: var(--sa-track, rgba(255, 255, 255, 0.08));
		border-radius: var(--sa-radius, 8px);
	}
	.scroll-area::-webkit-scrollbar-thumb {
		background: var(--sa-thumb, rgba(255, 255, 255, 0.35));
		border-radius: var(--sa-radius, 8px);
		/* Create padding around thumb for a nicer look */
		border: 2px solid transparent;
		background-clip: padding-box;
	}
	.scroll-area:hover::-webkit-scrollbar-thumb {
		background: var(--sa-thumb-hover, rgba(255, 255, 255, 0.55));
	}

	/* Auto-hide variant: keep thumb transparent until hover for a sleeker feel */
	.scroll-area.auto-hide::-webkit-scrollbar-thumb {
		background: transparent;
	}
	.scroll-area.auto-hide:hover::-webkit-scrollbar-thumb {
		background: var(--sa-thumb, rgba(255, 255, 255, 0.35));
	}
</style>

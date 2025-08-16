<script lang="ts">
	export let size: number = 16;
	export let className: string = '';
</script>

<svg
	xmlns="http://www.w3.org/2000/svg"
	class={`animate-spin ${className}`}
	width={size}
	height={size}
	viewBox="0 0 24 24"
	fill="none"
	aria-hidden="true"
	role="img"
>
	<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
	<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
</svg>

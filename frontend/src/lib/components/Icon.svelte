<script lang="ts" module>
	const paths = {
		search: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
		plus: 'M12 4v16m8-8H4',
		close: 'M6 18L18 6M6 6l12 12',
		sliders:
			'M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4'
	} as const;

	export type IconName = keyof typeof paths;
</script>

<script lang="ts">
	let { name, class: className = 'h-5 w-5' }: { name: IconName; class?: string } = $props();
</script>

<svg
	xmlns="http://www.w3.org/2000/svg"
	class={className}
	fill="none"
	viewBox="0 0 24 24"
	stroke="currentColor"
	aria-hidden="true"
>
	<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={paths[name]} />
</svg>

<script lang="ts" module>
	const paths = {
		search: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
		plus: 'M12 4v16m8-8H4',
		'arrow-left': 'M10 19l-7-7m0 0l7-7m-7 7h18',
		upload: 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12',
		close: 'M6 18L18 6M6 6l12 12',
		lock: 'M5 11h14a2 2 0 012 2v7a2 2 0 01-2 2H5a2 2 0 01-2-2v-7a2 2 0 012-2zm2 0V7a5 5 0 0110 0v4',
		eye: 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8zm11 3a3 3 0 100-6 3 3 0 000 6z',
		'eye-off':
			'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8zm11 3a3 3 0 100-6 3 3 0 000 6zM3 3l18 18',
		sliders:
			'M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4'
	} as const;

	export type IconName = keyof typeof paths;
</script>

<script lang="ts">
	type Props = {
		class?: string;
		name: IconName;
	};

	let { class: className = 'h-5 w-5', name }: Props = $props();
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

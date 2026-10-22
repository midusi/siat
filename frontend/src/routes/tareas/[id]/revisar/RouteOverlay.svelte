<script lang="ts">
	import * as review from './review';

	type Props = {
		animating: boolean;
		fadingOut: boolean;
		futureSegments: Array<Array<review.Point>>;
		pastSegments: Array<Array<review.Point>>;
	};

	const SEGMENT_DELAY_MS: number = 35;

	let { animating, fadingOut, futureSegments, pastSegments }: Props = $props();
</script>

{#snippet routeLine(seg: Array<review.Point>, i: number, past: boolean)}
	{#if seg.length > 1}
		<polyline
			points={(past ? [...seg].reverse() : seg).map((p) => `${p.x},${p.y}`).join(' ')}
			fill="none"
			stroke="#ffffff"
			stroke-width={past ? 2.5 : 2}
			stroke-linecap="round"
			stroke-linejoin="round"
			opacity={past ? undefined : 0.5}
			filter={past ? 'url(#white-glow)' : undefined}
			pathLength="1"
			class={[animating && '[stroke-dasharray:1] [stroke-dashoffset:1] animate-draw-in']}
			style:animation-delay={animating ? `${i * SEGMENT_DELAY_MS}ms` : undefined}
		/>
	{/if}
{/snippet}

<svg
	class="absolute inset-0 z-[13] pointer-events-none transition-opacity duration-500"
	class:opacity-0={fadingOut}
	width="100%"
	height="100%"
>
	<defs>
		<filter id="white-glow" x="-50%" y="-50%" width="200%" height="200%">
			<feGaussianBlur stdDeviation="2.5" result="coloredBlur" />
			<feMerge>
				<feMergeNode in="coloredBlur" />
				<feMergeNode in="SourceGraphic" />
			</feMerge>
		</filter>
	</defs>
	{#each pastSegments as seg, i (i)}
		{@render routeLine(seg, i, true)}
	{/each}
	{#each futureSegments as seg, i (i)}
		{@render routeLine(seg, i, false)}
	{/each}
</svg>

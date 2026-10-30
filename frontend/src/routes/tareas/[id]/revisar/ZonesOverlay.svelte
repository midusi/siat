<script lang="ts">
	import { RESERVED_COLORS } from '$lib/colors';
	import * as review from './review';
	import { warpPolygon } from '$lib/camera-motion';

	import type { MotionMatrix } from '$lib/camera-motion';

	type Props = {
		excludedZones: Array<Array<review.Vertex>>;
		matrix: MotionMatrix;
		roadsIn: Array<review.RoadPoly>;
		roadsOut: Array<review.RoadPoly>;
		scale: review.Scale;
	};

	let { excludedZones, matrix, roadsIn, roadsOut, scale }: Props = $props();

	const toPoints = (poly: Array<review.Vertex>): string =>
		review.scalePolygon(warpPolygon(poly, matrix), scale);
</script>

{#snippet roadPolygons(
	roads: Array<review.RoadPoly>,
	fill: string,
	stroke: string,
	fallbackName: string
)}
	{#each roads as r (r.id)}
		<polygon points={toPoints(r.polygon)} {fill} {stroke} stroke-width="2">
			<title>{r.name || fallbackName}</title>
		</polygon>
	{/each}
{/snippet}

<svg class="absolute inset-0 z-[11] pointer-events-none" width="100%" height="100%">
	{@render roadPolygons(roadsIn, 'rgba(16,185,129,0.20)', RESERVED_COLORS.green, 'Entrada')}
	{@render roadPolygons(roadsOut, 'rgba(239,68,68,0.20)', RESERVED_COLORS.red, 'Salida')}
	{#each excludedZones as poly, i (i)}
		<polygon
			points={toPoints(poly)}
			fill={RESERVED_COLORS.black}
			stroke={RESERVED_COLORS.black}
			stroke-width="2"
		/>
	{/each}
</svg>

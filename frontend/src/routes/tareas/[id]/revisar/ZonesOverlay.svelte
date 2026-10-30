<script lang="ts">
	import { RESERVED_COLORS } from '$lib/colors';
	import * as review from './review';

	type Props = {
		excludedZones: Array<Array<review.Vertex>>;
		roadsIn: Array<review.RoadPoly>;
		roadsOut: Array<review.RoadPoly>;
		scale: review.Scale;
	};

	let { excludedZones, roadsIn, roadsOut, scale }: Props = $props();
</script>

{#snippet roadPolygons(
	roads: Array<review.RoadPoly>,
	fill: string,
	stroke: string,
	fallbackName: string
)}
	{#each roads as r (r.id)}
		<polygon points={review.scalePolygon(r.polygon, scale)} {fill} {stroke} stroke-width="2">
			<title>{r.name || fallbackName}</title>
		</polygon>
	{/each}
{/snippet}

<svg class="absolute inset-0 z-[11] pointer-events-none" width="100%" height="100%">
	{@render roadPolygons(roadsIn, 'rgba(16,185,129,0.20)', RESERVED_COLORS.green, 'Entrada')}
	{@render roadPolygons(roadsOut, 'rgba(239,68,68,0.20)', RESERVED_COLORS.red, 'Salida')}
	{#each excludedZones as poly, i (i)}
		<polygon
			points={review.scalePolygon(poly, scale)}
			fill={RESERVED_COLORS.black}
			stroke={RESERVED_COLORS.black}
			stroke-width="2"
		/>
	{/each}
</svg>

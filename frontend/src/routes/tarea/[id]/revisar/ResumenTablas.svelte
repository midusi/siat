<script lang="ts">
	import * as review from './review';

	let {
		rutas,
		vehicleTypes,
		classColor
	}: {
		rutas: review.Rutas;
		vehicleTypes: string[];
		classColor: (cls: string) => string;
	} = $props();

	let entradas = $derived(review.buildTablaEntradas(rutas, vehicleTypes));
	let salidas = $derived(review.buildTablaSalidas(rutas, vehicleTypes));
	let porEntrada = $derived(review.buildTablasPorEntrada(rutas, vehicleTypes));
</script>

{#snippet tabla(t: review.Tabla)}
	<div class="overflow-x-auto">
		<table class="w-full text-sm text-left">
			<thead class="text-xs uppercase glass-surface">
				<tr>
					<th scope="col" class="px-4 py-3">Vehículo</th>
					{#each t.columnas as col (col)}
						<th scope="col" class="px-4 py-3 text-center">{col}</th>
					{/each}
				</tr>
			</thead>
			<tbody>
				{#each t.datos as fila (fila.__key ?? fila.tipo)}
					<tr class="border-b border-[hsl(var(--border))] hover:bg-[hsl(var(--card))]">
						<td class="px-4 py-2 font-medium whitespace-nowrap">
							{#if fila.__key}
								<span class="color-dot" style:background={classColor(fila.__key)}></span>
							{/if}
							{fila.tipo}
						</td>
						{#each t.columnas as col (col)}
							<td class="px-4 py-2 text-center">{fila[col]}</td>
						{/each}
					</tr>
				{/each}
				<tr class="font-semibold glass-surface">
					<td class="px-4 py-2">{t.total.tipo}</td>
					{#each t.columnas as col (col)}
						<td class="px-4 py-2 text-center">{t.total[col]}</td>
					{/each}
				</tr>
			</tbody>
		</table>
	</div>
{/snippet}

<div class="max-w-7xl mx-auto space-y-12">
	<div class="grid grid-cols-1 md:grid-cols-2 gap-8">
		<div class="glass-card p-6 rounded-lg shadow-lg">
			<h2 class="text-2xl font-semibold mb-4 text-center">Resumen de Entradas por Zona</h2>
			{@render tabla(entradas)}
		</div>
		<div class="glass-card p-6 rounded-lg shadow-lg">
			<h2 class="text-2xl font-semibold mb-4 text-center">Resumen de Salidas por Zona</h2>
			{@render tabla(salidas)}
		</div>
	</div>

	<div class="glass-card p-6 rounded-lg shadow-lg">
		<h2 class="text-2xl font-semibold mb-6 text-center">Detalle de Rutas (Entrada -> Salida)</h2>
		<div class="space-y-8">
			{#each porEntrada as entrada (entrada.nombreEntrada)}
				<div>
					<h3 class="text-xl font-medium mb-3 opacity-80">{entrada.nombreEntrada}</h3>
					{@render tabla(entrada)}
				</div>
			{/each}
		</div>
	</div>
</div>

<script lang="ts">
	import { onMount } from 'svelte';
	import { BACKEND_URL } from '$lib/constants';

	// --- Props y estado inicial ---
	let { data } = $props();
	let loading = $state(true);
	let error = $state<string | null>(null);

	// --- Definiciones de Tipos ---
	type Vehiculo = 'bicycle' | 'bus' | 'car' | 'heavy_truck' | 'light_truck' | 'motorbike';
	type ConteoVehiculos = { [key in Vehiculo]: number };
	type Rutas = { [entrada: string]: { [salida: string]: ConteoVehiculos } };
	type Indeterminados = { [trackId: string]: [string, string] };
	type FilaTabla = { tipo: string; [key: string]: string | number };

	// --- Estado reactivo para los datos de la API ---
	let videoPath = $state('');
	let rutas = $state<Rutas>({});
	let indeterminados = $state<Indeterminados>({});

	// --- Constantes y funciones de ayuda ---
	const VEHICLE_TYPES: Vehiculo[] = [
		'car',
		'motorbike',
		'bus',
		'light_truck',
		'heavy_truck',
		'bicycle'
	];
	const VEHICLE_NAMES: Record<Vehiculo, string> = {
		car: 'Automóvil',
		motorbike: 'Motocicleta',
		bus: 'Autobús',
		light_truck: 'Camión Ligero',
		heavy_truck: 'Camión Pesado',
		bicycle: 'Bicicleta'
	};

	// --- FUNCIÓN PARA ETIQUETAS ALFABÉTICAS ---
	function getLetterLabel(id: string): string {
		const numericId = parseInt(id, 10);
		if (isNaN(numericId)) return id;
		return String.fromCharCode(65 + numericId);
	}

	// --- Función para obtener los datos del backend ---
	async function fetchData(taskId: string) {
		loading = true;
		error = null;
		try {
			const res = await fetch(`${BACKEND_URL}/task/${taskId}`);
			if (!res.ok) throw new Error(`Error al obtener datos: ${res.statusText}`);
			const apiData = await res.json();
			videoPath = apiData.videoPath;
			rutas = apiData.rutas;
			indeterminados = apiData.indeterminados;
		} catch (e: any) {
			error = e.message || 'Error desconocido al cargar los datos.';
		} finally {
			loading = false;
		}
	}

	// --- Lógica de carga ---
	onMount(() => {
		const taskId = data.id;
		if (taskId) fetchData(taskId);
		else {
			error = 'No se proporcionó un ID de tarea.';
			loading = false;
		}
	});

	// --- Transformación de datos usando $derived (CON ETIQUETAS ALFABÉTICAS) ---

	// 1. Datos para la tabla de ENTRADAS
	let entradasData = $derived.by(() => {
		if (Object.keys(rutas).length === 0) return null;
		const entradasIds = Object.keys(rutas).sort();
		const columnasPrincipales = entradasIds.map((id) => `Entrada ${getLetterLabel(id)}`);
		const totalGeneral: FilaTabla = {
			tipo: 'Total',
			...Object.fromEntries(columnasPrincipales.map((c) => [c, 0]))
		};
		const datos = VEHICLE_TYPES.map((vehiculo) => {
			const fila: FilaTabla = { tipo: VEHICLE_NAMES[vehiculo] };
			entradasIds.forEach((entradaId) => {
				const nombreColumna = `Entrada ${getLetterLabel(entradaId)}`;
				const totalVehiculoPorEntrada = Object.values(rutas[entradaId] || {}).reduce(
					(sum, salida) => sum + (salida[vehiculo] ?? 0),
					0
				);
				fila[nombreColumna] = totalVehiculoPorEntrada;
				(totalGeneral[nombreColumna] as number) += totalVehiculoPorEntrada;
			});
			return fila;
		});
		return {
			titulo: 'Resumen de Entradas por Zona',
			columnasPrincipales,
			datos,
			total: totalGeneral
		};
	});

	// 2. Datos para la tabla de SALIDAS
	let salidasData = $derived.by(() => {
		if (Object.keys(rutas).length === 0) return null;
		const salidasIds = [...new Set(Object.values(rutas).flatMap(Object.keys))].sort();
		const columnasPrincipales = salidasIds.map((id) => `Salida ${getLetterLabel(id)}`);
		const totalGeneral: FilaTabla = {
			tipo: 'Total',
			...Object.fromEntries(columnasPrincipales.map((c) => [c, 0]))
		};
		const datos = VEHICLE_TYPES.map((vehiculo) => {
			const fila: FilaTabla = { tipo: VEHICLE_NAMES[vehiculo] };
			salidasIds.forEach((salidaId) => {
				const nombreColumna = `Salida ${getLetterLabel(salidaId)}`;
				let totalVehiculoPorSalida = 0;
				for (const entradaId in rutas) {
					totalVehiculoPorSalida += rutas[entradaId]?.[salidaId]?.[vehiculo] ?? 0;
				}
				fila[nombreColumna] = totalVehiculoPorSalida;
				(totalGeneral[nombreColumna] as number) += totalVehiculoPorSalida;
			});
			return fila;
		});
		return {
			titulo: 'Resumen de Salidas por Zona',
			columnasPrincipales,
			datos,
			total: totalGeneral
		};
	});

	// 3. Datos para la tabla detallada de RUTAS
	let rutasData = $derived.by(() => {
		if (Object.keys(rutas).length === 0) return null;
		const entradasIds = Object.keys(rutas).sort();
		const entradasDetalle = entradasIds.map((entradaId) => {
			const salidasDeEntradaIds = Object.keys(rutas[entradaId]).sort();
			const columnasSalida = salidasDeEntradaIds.map((id) => `Salida ${getLetterLabel(id)}`);
			const totalEntrada: FilaTabla = {
				tipo: 'Total',
				...Object.fromEntries(columnasSalida.map((c) => [c, 0]))
			};
			const datos = VEHICLE_TYPES.map((vehiculo) => {
				const fila: FilaTabla = { tipo: VEHICLE_NAMES[vehiculo] };
				salidasDeEntradaIds.forEach((salidaId) => {
					const nombreColumna = `Salida ${getLetterLabel(salidaId)}`;
					const conteo = rutas[entradaId][salidaId][vehiculo] ?? 0;
					fila[nombreColumna] = conteo;
					(totalEntrada[nombreColumna] as number) += conteo;
				});
				return fila;
			});
			return {
				nombreEntrada: `Desde Entrada ${getLetterLabel(entradaId)}`,
				columnasSalida,
				datos,
				total: totalEntrada
			};
		});
		return { titulo: 'Detalle de Rutas (Entrada -> Salida)', entradasDetalle };
	});

	// 4. Datos para la tabla de INDETERMINADOS
	let indeterminadosData = $derived.by(() => {
		if (Object.keys(indeterminados).length === 0) return null;
		return Object.entries(indeterminados).map(([trackId, [entrada, salida]]) => ({
			trackId,
			entrada: entrada === 'IND' ? 'Indeterminada' : `Zona ${getLetterLabel(entrada)}`,
			salida: salida === 'IND' ? 'Indeterminada' : `Zona ${getLetterLabel(salida)}`
		}));
	});
</script>

<!-- Tu código HTML permanece exactamente igual -->
<div class="min-h-screen bg-[#1a1e2a] text-white py-8 px-4">
	<div class="max-w-7xl mx-auto">
		<h1 class="text-3xl font-bold mb-8 text-center">Revisar Video Analizado</h1>

		{#if loading}
			<p class="text-center text-xl">Cargando datos de la tarea...</p>
		{:else if error}
			<div
				class="bg-red-900 border border-red-600 text-red-100 px-4 py-3 rounded-lg text-center"
				role="alert"
			>
				<strong class="font-bold">¡Error!</strong>
				<span class="block sm:inline">{error}</span>
			</div>
		{:else}
			<!-- Video Player -->
			{#if videoPath !== ''}
				<div class="rounded overflow-hidden border border-gray-600 bg-black mb-12">
					<video class="w-full" controls autoplay>
						<!-- 'autoplay' es opcional pero útil para ver el efecto -->
						<source src={videoPath} type="video/mp4" />
						<track kind="captions" />
						Tu navegador no soporta la reproducción de video.
					</video>
				</div>
			{/if}

			<!-- Sección de Estadísticas -->
			<div class="space-y-12">
				<!-- Tablas de Resumen (Entradas y Salidas) -->
				<div class="grid grid-cols-1 md:grid-cols-2 gap-8">
					<!-- Tabla de Entradas -->
					{#if entradasData}
						<div class="bg-[#2a2f3a] p-6 rounded-lg shadow-lg">
							<h2 class="text-2xl font-semibold mb-4 text-center">{entradasData.titulo}</h2>
							<div class="overflow-x-auto">
								<table class="w-full text-sm text-left">
									<thead class="text-xs text-gray-300 uppercase bg-[#383f4f]">
										<tr>
											<th scope="col" class="px-4 py-3">Vehículo</th>
											{#each entradasData.columnasPrincipales as col}
												<th scope="col" class="px-4 py-3 text-center">{col}</th>
											{/each}
										</tr>
									</thead>
									<tbody>
										{#each entradasData.datos as item}
											<tr class="border-b border-gray-700 hover:bg-[#383f4f]">
												<td class="px-4 py-2 font-medium whitespace-nowrap">{item.tipo}</td>
												{#each entradasData.columnasPrincipales as col}
													<td class="px-4 py-2 text-center">{item[col]}</td>
												{/each}
											</tr>
										{/each}
										<tr class="font-semibold bg-[#383f4f]">
											<td class="px-4 py-2">{entradasData.total.tipo}</td>
											{#each entradasData.columnasPrincipales as col}
												<td class="px-4 py-2 text-center">{entradasData.total[col]}</td>
											{/each}
										</tr>
									</tbody>
								</table>
							</div>
						</div>
					{/if}

					<!-- Tabla de Salidas -->
					{#if salidasData}
						<div class="bg-[#2a2f3a] p-6 rounded-lg shadow-lg">
							<h2 class="text-2xl font-semibold mb-4 text-center">{salidasData.titulo}</h2>
							<div class="overflow-x-auto">
								<table class="w-full text-sm text-left">
									<thead class="text-xs text-gray-300 uppercase bg-[#383f4f]">
										<tr>
											<th scope="col" class="px-4 py-3">Vehículo</th>
											{#each salidasData.columnasPrincipales as col}
												<th scope="col" class="px-4 py-3 text-center">{col}</th>
											{/each}
										</tr>
									</thead>
									<tbody>
										{#each salidasData.datos as item}
											<tr class="border-b border-gray-700 hover:bg-[#383f4f]">
												<td class="px-4 py-2 font-medium whitespace-nowrap">{item.tipo}</td>
												{#each salidasData.columnasPrincipales as col}
													<td class="px-4 py-2 text-center">{item[col]}</td>
												{/each}
											</tr>
										{/each}
										<tr class="font-semibold bg-[#383f4f]">
											<td class="px-4 py-2">{salidasData.total.tipo}</td>
											{#each salidasData.columnasPrincipales as col}
												<td class="px-4 py-2 text-center">{salidasData.total[col]}</td>
											{/each}
										</tr>
									</tbody>
								</table>
							</div>
						</div>
					{/if}
				</div>

				<!-- Tabla detallada de Rutas -->
				{#if rutasData}
					<div class="bg-[#2a2f3a] p-6 rounded-lg shadow-lg">
						<h2 class="text-2xl font-semibold mb-6 text-center">{rutasData.titulo}</h2>
						<div class="space-y-8">
							{#each rutasData.entradasDetalle as entrada}
								<div>
									<h3 class="text-xl font-medium mb-3 text-gray-300">{entrada.nombreEntrada}</h3>
									<div class="overflow-x-auto">
										<table class="w-full text-sm text-left">
											<thead class="text-xs text-gray-300 uppercase bg-[#383f4f]">
												<tr>
													<th scope="col" class="px-4 py-3">Vehículo</th>
													{#each entrada.columnasSalida as colName}
														<th scope="col" class="px-4 py-3 text-center">{colName}</th>
													{/each}
												</tr>
											</thead>
											<tbody>
												{#each entrada.datos as item}
													<tr class="border-b border-gray-700 hover:bg-[#383f4f]">
														<td class="px-4 py-2 font-medium whitespace-nowrap">{item.tipo}</td>
														{#each entrada.columnasSalida as colName}
															<td class="px-4 py-2 text-center">{item[colName]}</td>
														{/each}
													</tr>
												{/each}
												<tr class="font-semibold bg-[#383f4f]">
													<td class="px-4 py-2">{entrada.total.tipo}</td>
													{#each entrada.columnasSalida as colName}
														<td class="px-4 py-2 text-center">{entrada.total[colName]}</td>
													{/each}
												</tr>
											</tbody>
										</table>
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Tabla de Vehículos Indeterminados -->
				{#if indeterminadosData}
					<div class="bg-[#2a2f3a] p-6 rounded-lg shadow-lg">
						<h2 class="text-2xl font-semibold mb-4 text-center">
							Vehículos con Trayectoria Indeterminada
						</h2>
						<div class="overflow-x-auto">
							<table class="w-full text-sm text-left">
								<thead class="text-xs text-gray-300 uppercase bg-[#383f4f]">
									<tr>
										<th scope="col" class="px-4 py-3">Track ID</th>
										<th scope="col" class="px-4 py-3">Entrada Detectada</th>
										<th scope="col" class="px-4 py-3">Salida Detectada</th>
									</tr>
								</thead>
								<tbody>
									{#each indeterminadosData as item}
										<tr class="border-b border-gray-700 hover:bg-[#383f4f]">
											<td class="px-4 py-2 font-medium">{item.trackId}</td>
											<td class="px-4 py-2">{item.entrada}</td>
											<td class="px-4 py-2">{item.salida}</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>

<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { BACKEND_URL } from '$lib/constants';

	// --- Props y estado inicial ---
	let { data } = $props();
	let loading = $state(true);
	let error = $state<string | null>(null);
	let notification = $state<string | null>(null);

	// --- Referencias a elementos del DOM ---
	let videoElement = $state<HTMLVideoElement | null>(null);
	let videoHeightPx = $state(0);

	// --- Definiciones de Tipos ---
	type Vehiculo = string;
	type ConteoVehiculos = { [key: Vehiculo]: number };
	type Rutas = { [entrada: string]: { [salida: string]: ConteoVehiculos } };
	type BoundingBox = [string, string, string, string];
	type Indeterminado = {
		frame: string;
		class: Vehiculo;
		boundingBox: BoundingBox;
		labels: [string, string];
	};
	type Indeterminados = { [trackId: string]: Indeterminado };
	type FilaTabla = { tipo: string; [key: string]: string | number };

	// --- Estado reactivo para los datos de la API ---
	let videoPath = $state('');
	let videoWidth = $state(0);
	let videoHeight = $state(0);
	let videoFps = $state(0);
	let rutas = $state<Rutas>({});
	let indeterminados = $state<Indeterminados>({});

	function syncHeight() {
		if (videoElement) {
			// Medimos la altura renderizada del video y la guardamos en nuestro estado.
			videoHeightPx = videoElement.clientHeight;
		}
		console.log(videoHeightPx);
	}

	function getVehicleName(key: Vehiculo): string {
		if (!key) return 'N/A';
		return key.charAt(0).toUpperCase() + key.slice(1).toLowerCase().replaceAll(/_/g, ' ');
	}

	function showNotification(message: string, duration: number = 3000) {
		notification = message;
		setTimeout(() => {
			notification = null;
		}, duration);
	}

	async function updateBackendData() {
		try {
			const res = await fetch(`${BACKEND_URL}/task/${data.id}/update-data`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					rutas: rutas,
					indeterminados: indeterminados
				})
			});
			if (!res.ok) throw new Error('No se pudo guardar los cambios en el servidor.');
			console.log('Datos actualizados en el backend.');
			console.log('Response:', await res.json());
			console.log('Rutas:', rutas);
			console.log('Indeterminados:', indeterminados);
		} catch (e: any) {
			error = e.message;
		}
	}

	async function fetchData(taskId: string) {
		loading = true;
		error = null;
		try {
			const res = await fetch(`${BACKEND_URL}/task/${taskId}`);
			if (!res.ok) throw new Error(`Error al obtener datos: ${res.statusText}`);
			const apiData = await res.json();
			videoPath = apiData.videoPath;
			videoWidth = +apiData.videoWidth;
			videoHeight = +apiData.videoHeight;
			videoFps = +apiData.videoFps;
			rutas = apiData.rutas;
			indeterminados = apiData.indeterminados;
		} catch (e: any) {
			error = e.message || 'Error desconocido al cargar los datos.';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		const taskId = data.id;
		if (taskId) fetchData(taskId);
		else {
			error = 'No se proporcionó un ID de tarea.';
			loading = false;
		}

		// Sincronizar altura cuando la ventana cambie de tamaño
		window.addEventListener('resize', syncHeight);
	});

	// --- LÓGICA DE INTERACCIÓN SIMPLIFICADA ---
	function handleIndeterminateClick(trackId: string) {
		if (!videoElement || !videoFps) return;
		const item = indeterminados[trackId];
		if (!item) return;

		const timeInSeconds = parseInt(item.frame) / videoFps;
		videoElement.currentTime = timeInSeconds;
		videoElement.pause();
	}

	function handleKeyPress(event: KeyboardEvent, trackId: string) {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			handleIndeterminateClick(trackId);
		}
	}

	// --- Lógica de Corrección de Datos ---
	function handleConfirm(trackId: string, event: MouseEvent) {
		event.stopPropagation();
		const item = indeterminados[trackId];
		const [entrada, salida] = item.labels;
		const vehiculo = item.class;

		if (rutas[entrada]?.[salida]?.[vehiculo] !== undefined) {
			rutas[entrada][salida][vehiculo]++;
		} else {
			if (!rutas[entrada]) rutas[entrada] = {};
			if (!rutas[entrada][salida]) rutas[entrada][salida] = {};
			vehicleTypes.forEach((v) => {
				if (rutas[entrada][salida][v] === undefined) {
					rutas[entrada][salida][v] = 0;
				}
			});
			rutas[entrada][salida][vehiculo] = 1;
		}

		delete indeterminados[trackId];
		indeterminados = { ...indeterminados };
		rutas = { ...rutas };
		showNotification(`Vehículo ${trackId} confirmado y añadido a la ruta ${entrada} -> ${salida}.`);
		updateBackendData();
	}

	function handleDelete(trackId: string, event: MouseEvent) {
		event.stopPropagation();
		delete indeterminados[trackId];
		indeterminados = { ...indeterminados };
		showNotification(`Vehículo indeterminado ${trackId} eliminado.`);
		updateBackendData();
	}

	// --- Derivaciones de Datos para la UI ---
	let vehicleTypes = $derived.by(() => {
		if (Object.keys(rutas).length === 0) return [];
		const allTypes = new Set<string>();
		for (const entrada in rutas) {
			for (const salida in rutas[entrada]) {
				Object.keys(rutas[entrada][salida]).forEach((vehiculo) => allTypes.add(vehiculo));
			}
		}
		Object.values(indeterminados).forEach((item) => allTypes.add(item.class));
		return Array.from(allTypes).sort();
	});

	let zoneIds = $derived.by(() => {
		if (Object.keys(rutas).length === 0) return [];
		const allZones = new Set<string>();
		Object.keys(rutas).forEach((id) => allZones.add(id));
		Object.values(rutas).forEach((salidas) =>
			Object.keys(salidas).forEach((id) => allZones.add(id))
		);
		return Array.from(allZones).sort();
	});

	let sortedIndeterminados = $derived.by(() => {
		return Object.entries(indeterminados).sort(([, a], [, b]) => {
			const aIsEntradaConocida = a.labels[0] !== 'IND' && a.labels[1] === 'IND';
			const bIsEntradaConocida = b.labels[0] !== 'IND' && b.labels[1] === 'IND';
			if (aIsEntradaConocida && !bIsEntradaConocida) return -1;
			if (!aIsEntradaConocida && bIsEntradaConocida) return 1;
			return parseInt(a.frame) - parseInt(b.frame);
		});
	});

	// Datos para la tabla de ENTRADAS
	let entradasData = $derived.by(() => {
		if (Object.keys(rutas).length === 0) return null;
		const entradasIds = Object.keys(rutas).sort();
		const columnasPrincipales = entradasIds.map((id) => `Entrada ${id}`);
		const totalGeneral: FilaTabla = {
			tipo: 'Total',
			...Object.fromEntries(columnasPrincipales.map((c) => [c, 0]))
		};
		const datos = vehicleTypes.map((vehiculo) => {
			const fila: FilaTabla = { tipo: getVehicleName(vehiculo) };
			entradasIds.forEach((entradaId) => {
				const nombreColumna = `Entrada ${entradaId}`;
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

	// Datos para la tabla de SALIDAS
	let salidasData = $derived.by(() => {
		if (Object.keys(rutas).length === 0) return null;
		const salidasIds = [...new Set(Object.values(rutas).flatMap(Object.keys))].sort();
		const columnasPrincipales = salidasIds.map((id) => `Salida ${id}`);
		const totalGeneral: FilaTabla = {
			tipo: 'Total',
			...Object.fromEntries(columnasPrincipales.map((c) => [c, 0]))
		};
		const datos = vehicleTypes.map((vehiculo) => {
			const fila: FilaTabla = { tipo: getVehicleName(vehiculo) };
			salidasIds.forEach((salidaId) => {
				const nombreColumna = `Salida ${salidaId}`;
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

	// Datos para la tabla detallada de RUTAS
	let rutasData = $derived.by(() => {
		if (Object.keys(rutas).length === 0) return null;
		const entradasIds = Object.keys(rutas).sort();
		const entradasDetalle = entradasIds.map((entradaId) => {
			const salidasDeEntradaIds = Object.keys(rutas[entradaId]).sort();
			const columnasSalida = salidasDeEntradaIds.map((id) => `Salida ${id}`);
			const totalEntrada: FilaTabla = {
				tipo: 'Total',
				...Object.fromEntries(columnasSalida.map((c) => [c, 0]))
			};
			const datos = vehicleTypes.map((vehiculo) => {
				const fila: FilaTabla = { tipo: getVehicleName(vehiculo) };
				salidasDeEntradaIds.forEach((salidaId) => {
					const nombreColumna = `Salida ${salidaId}`;
					const conteo = rutas[entradaId][salidaId][vehiculo] ?? 0;
					fila[nombreColumna] = conteo;
					(totalEntrada[nombreColumna] as number) += conteo;
				});
				return fila;
			});
			return {
				nombreEntrada: `Desde Entrada ${entradaId}`,
				columnasSalida,
				datos,
				total: totalEntrada
			};
		});
		return { titulo: 'Detalle de Rutas (Entrada -> Salida)', entradasDetalle };
	});
</script>

<!-- Notificación Flotante -->
{#if notification}
	<div class="fixed top-5 right-5 bg-green-600 text-white py-2 px-4 rounded-lg shadow-lg z-50">
		{notification}
	</div>
{/if}

<div class="min-h-screen bg-[#1a1e2a] text-white py-8 px-4">
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
		<!-- Contenedor Flexbox para centrar el video y la lista -->
		<div class="flex flex-wrap justify-center items-start gap-8 mb-12">
			<!-- Columna de Video (ahora un item de flex) -->
			<div class="w-full lg:w-2/3 max-w-5xl">
				{#if videoPath !== ''}
					<div class="rounded overflow-hidden border border-gray-600 bg-black aspect-video">
						<video
							class="w-full h-full"
							controls
							autoplay
							bind:this={videoElement}
							onloadedmetadata={syncHeight}
						>
							<source src={videoPath} type="video/mp4" />
							<track kind="captions" />
							Tu navegador no soporta la reproducción de video.
						</video>
					</div>
				{/if}
			</div>

			<!-- Columna de Indeterminados (ahora un item de flex) -->
			{#if sortedIndeterminados.length > 0}
				<div
					class="w-full md:w-auto bg-[#2a2f3a] p-4 rounded-lg shadow-lg max-w-[450px] overflow-y-auto"
					style:height={videoHeightPx > 0 ? `${videoHeightPx}px` : 'auto'}
				>
					<h3 class="text-xl font-semibold mb-4 text-center">Vehículos Indeterminados</h3>

					<div class="overflow-y-auto flex-1">
						<div class="space-y-3">
							{#each sortedIndeterminados as [trackId, item] (trackId)}
								{@const [entrada, salida] = item.labels}
								{@const canConfirm = entrada !== 'IND' && salida !== 'IND'}
								<div
									class="bg-[#383f4f] p-3 rounded-md border border-gray-600 cursor-pointer hover:border-emerald-500 transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-400"
									role="button"
									tabindex="0"
									onclick={() => handleIndeterminateClick(trackId)}
									onkeydown={(e) => handleKeyPress(e, trackId)}
								>
									<!-- El resto del contenido de la tarjeta de indeterminado va aquí... -->
									<!-- ... (no es necesario pegarlo todo, solo asegúrate de que esté dentro de este div) -->
									<div class="flex justify-between items-center mb-2">
										<p class="font-bold text-lg">ID: {trackId}</p>
										<button
											onclick={(e) => handleDelete(trackId, e)}
											class="text-red-400 hover:text-red-300 text-xs">Eliminar</button
										>
									</div>
									<div class="grid grid-cols-3 gap-2 items-center mb-2 text-sm">
										<label for="class-{trackId}" class="text-gray-400">Clase:</label>
										<select
											id="class-{trackId}"
											bind:value={indeterminados[trackId].class}
											onclick={(e) => e.stopPropagation()}
											class="col-span-2 bg-[#2a2f3a] border border-gray-500 rounded px-2 py-1 w-full"
										>
											{#each vehicleTypes as type}
												<option value={type}>{getVehicleName(type)}</option>
											{/each}
										</select>
									</div>
									<div class="grid grid-cols-3 gap-2 items-center mb-3 text-sm">
										<label for="entrada-{trackId}" class="text-gray-400">Ruta:</label>
										<div class="col-span-2 flex items-center gap-1">
											<select
												id="entrada-{trackId}"
												bind:value={indeterminados[trackId].labels[0]}
												onclick={(e) => e.stopPropagation()}
												class="bg-[#2a2f3a] border border-gray-500 rounded px-2 py-1 w-full"
											>
												<option value="IND">IND</option>
												{#each zoneIds as zone}
													<option value={zone}>Zona {zone}</option>
												{/each}
											</select>
											<span class="text-gray-400">→</span>
											<select
												id="salida-{trackId}"
												bind:value={indeterminados[trackId].labels[1]}
												onclick={(e) => e.stopPropagation()}
												class="bg-[#2a2f3a] border border-gray-500 rounded px-2 py-1 w-full"
											>
												<option value="IND">IND</option>
												{#each zoneIds as zone}
													<option value={zone}>Zona {zone}</option>
												{/each}
											</select>
										</div>
									</div>
									<button
										onclick={(e) => handleConfirm(trackId, e)}
										disabled={!canConfirm}
										class="w-full py-2 text-sm font-semibold rounded transition-colors"
										class:bg-emerald-600={canConfirm}
										class:hover:bg-emerald-500={canConfirm}
										class:bg-gray-500={!canConfirm}
										class:cursor-not-allowed={!canConfirm}
									>
										Confirmar Ruta
									</button>
								</div>
							{/each}
						</div>
					</div>
				</div>
			{/if}
		</div>

		<!-- Sección de Estadísticas -->
		<div class="max-w-7xl mx-auto space-y-12">
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
		</div>
	{/if}
</div>

<style>
	.overflow-y-auto::-webkit-scrollbar {
		width: 8px;
	}
	.overflow-y-auto::-webkit-scrollbar-track {
		background: #2a2f3a;
		border-radius: 10px;
	}
	.overflow-y-auto::-webkit-scrollbar-thumb {
		background-color: #4a5568;
		border-radius: 10px;
		border: 2px solid #2a2f3a;
	}
	.overflow-y-auto::-webkit-scrollbar-thumb:hover {
		background-color: #718096;
	}
</style>

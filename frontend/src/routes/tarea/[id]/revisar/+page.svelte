<script lang="ts">
	import { onMount } from 'svelte';
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
	// CAMBIO 1: Añadimos 'opacity' al tipo de la BBox que se va a renderizar.
	type DisplayableBBox = { id: string; bbox: BoundingBox; hideAtTime: number; opacity: number };

	// --- Estado reactivo ---
	let videoPath = $state('');
	let videoWidth = $state(0);
	let videoHeight = $state(0);
	let videoFps = $state(0);
	let rutas = $state<Rutas>({});
	let indeterminados = $state<Indeterminados>({});
	type SortedIndeterminado = [string, Indeterminado];
	let sortedIndeterminados = $state<SortedIndeterminado[]>([]);
	let videoScale = $state({ x: 1, y: 1 });

	// --- ESTADOS DE BBOX Y ANIMACIÓN ---
	let activeBoundingBox = $state<BoundingBox | null>(null);
	let playbackBoundingBoxes = $state<DisplayableBBox[]>([]);

	// ID del bucle de animación para poder cancelarlo
	let animationFrameId: number | null = null;
	// Para no volver a procesar el mismo frame en el bucle
	let lastProcessedFrame = -1;
	// CAMBIO 2: Renombramos la constante para que sea más claro que es la duración del desvanecimiento.
	const FADE_OUT_DURATION_SECONDS = 1.0;

	// --- ESTRUCTURA DE DATOS OPTIMIZADA POR FRAME ---
	let indeterminadosByFrame = $derived.by(() => {
		const map = new Map<number, { trackId: string; bbox: BoundingBox }[]>();
		if (!videoFps) return map;
		for (const [trackId, item] of Object.entries(indeterminados)) {
			const frame = parseInt(item.frame);
			if (!map.has(frame)) {
				map.set(frame, []);
			}
			map.get(frame)!.push({ trackId, bbox: item.boundingBox });
		}
		return map;
	});

	// --- LÓGICA DEL BUCLE DE ANIMACIÓN (MODIFICADA PARA DESVANECIMIENTO) ---
	function animationLoop() {
		if (!videoElement || videoElement.paused) {
			animationFrameId = null;
			return;
		}

		const currentTime = videoElement.currentTime;
		const currentFrame = Math.floor(currentTime * videoFps);

		// CAMBIO 3: Lógica de animación actualizada.
		// En lugar de eliminar bruscamente las bboxes, ahora actualizamos su opacidad
		// y solo las eliminamos del array cuando la opacidad es 0.
		if (playbackBoundingBoxes.length > 0) {
			playbackBoundingBoxes = playbackBoundingBoxes
				.map((box) => {
					const timeUntilHidden = box.hideAtTime - currentTime;
					// Calculamos la nueva opacidad. Será un valor entre 0 y 1.
					const newOpacity = Math.max(
						0,
						Math.min(1.0, timeUntilHidden / FADE_OUT_DURATION_SECONDS)
					);
					return { ...box, opacity: newOpacity };
				})
				.filter((box) => box.opacity > 0); // Solo mantenemos las que son visibles.
		}

		// 2. AÑADIR NUEVAS BBOXES si hemos avanzado a un nuevo frame
		if (currentFrame > lastProcessedFrame) {
			for (let frame = lastProcessedFrame + 1; frame <= currentFrame; frame++) {
				const bboxesInfo = indeterminadosByFrame.get(frame);
				if (bboxesInfo) {
					const newBoxes = bboxesInfo.map((info) => ({
						id: info.trackId,
						bbox: info.bbox,
						hideAtTime: frame / videoFps + FADE_OUT_DURATION_SECONDS,
						opacity: 1.0 // Empiezan con opacidad total
					}));
					playbackBoundingBoxes = [...playbackBoundingBoxes, ...newBoxes];
				}
			}
		}

		lastProcessedFrame = currentFrame;
		animationFrameId = requestAnimationFrame(animationLoop);
	}

	// --- FUNCIONES DE CONTROL DEL VIDEO ---
	function startAnimationLoop() {
		if (animationFrameId === null) {
			activeBoundingBox = null;
			activeIndeterminateId = null;
			playbackBoundingBoxes = [];

			// CAMBIO CLAVE:
			// En lugar de reiniciar siempre a -1, establecemos el último frame procesado
			// justo antes de la posición actual de reproducción. Esto evita que el bucle
			// "repase" la historia del video que fue omitida por una búsqueda (seek).
			if (videoElement && videoFps > 0) {
				lastProcessedFrame = Math.floor(videoElement.currentTime * videoFps) - 1;
			} else {
				lastProcessedFrame = -1;
			}

			animationFrameId = requestAnimationFrame(animationLoop);
		}
	}

	function stopAnimationLoop() {
		if (animationFrameId !== null) {
			cancelAnimationFrame(animationFrameId);
			animationFrameId = null;
		}
	}

	// CAMBIO 4: La BBox manual también debe tener una propiedad 'opacity' para ser consistente.
	let displayBoundingBoxes = $derived.by(() => {
		if (activeBoundingBox) {
			return [{ id: 'active-manual', bbox: activeBoundingBox, hideAtTime: Infinity, opacity: 1.0 }];
		}
		return playbackBoundingBoxes;
	});

	// --- Lógica de Interacción ---
	// IDs de las tarjetas que corresponden a BBoxes visibles en el video
	let liveIndeterminateIds = $derived.by(() => {
		// Usamos un Set para búsquedas ultra-rápidas (O(1)) en el template
		return new Set(playbackBoundingBoxes.map((box) => box.id));
	});
	let activeIndeterminateId = $state<string | null>(null);
	function handleIndeterminateClick(trackId: string) {
		activeIndeterminateId = trackId;
		if (!videoElement || !videoFps) return;
		const item = indeterminados[trackId];
		if (!item) return;

		stopAnimationLoop();
		videoElement.pause();

		const timeInSeconds = parseInt(item.frame) / videoFps;
		videoElement.currentTime = timeInSeconds;
		activeBoundingBox = item.boundingBox;
	}

	// --- El resto del código permanece casi igual ---
	function updateVideoDimensions() {
		if (videoElement) {
			videoHeightPx = videoElement.clientHeight;
			if (videoWidth > 0 && videoHeight > 0) {
				videoScale.x = videoElement.clientWidth / videoWidth;
				videoScale.y = videoElement.clientHeight / videoHeight;
			}
		}
	}
	// CAMBIO 5: La función ahora recibe el objeto `DisplayableBBox` completo.
	function calculateBoxStyle(box: DisplayableBBox): string {
		if (!videoElement) return 'display: none;';

		const { bbox, opacity } = box;
		const [x1_str, y1_str, x2_str, y2_str] = bbox;
		const x1 = parseFloat(x1_str),
			y1 = parseFloat(y1_str),
			x2 = parseFloat(x2_str),
			y2 = parseFloat(y2_str);

		let left = x1 * videoScale.x;
		let top = y1 * videoScale.y;
		let width = (x2 - x1) * videoScale.x;
		let height = (y2 - y1) * videoScale.y;

		const videoRenderedWidth = videoElement.clientWidth,
			videoRenderedHeight = videoElement.clientHeight;
		if (width < 0) {
			left += width;
			width = Math.abs(width);
		}
		if (height < 0) {
			top += height;
			height = Math.abs(height);
		}
		if (left < 0) {
			width += left;
			left = 0;
		}
		if (top < 0) {
			height += top;
			top = 0;
		}
		if (left + width > videoRenderedWidth) {
			width = videoRenderedWidth - left;
		}
		if (top + height > videoRenderedHeight) {
			height = videoRenderedHeight - top;
		}
		if (width <= 0 || height <= 0) return 'display: none;';

		// Añadimos la opacidad al estilo dinámico.
		return `position: absolute; left: ${left}px; top: ${top}px; width: ${width}px; height: ${height}px; opacity: ${opacity};`;
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

			// Meta del video
			videoPath = apiData.videoPath ?? '';
			videoWidth = +apiData.videoWidth;
			videoHeight = +apiData.videoHeight;
			videoFps = +apiData.videoFps;

			// Obtener rutas e indeterminados: inline o vía URLs públicas (MinIO)
			const rutasPromise: Promise<any> = apiData.rutas
				? Promise.resolve(apiData.rutas)
				: apiData.rutasUrl
					? fetch(apiData.rutasUrl)
							.then((r) => {
								if (!r.ok) throw new Error(`Error al obtener rutas: ${r.statusText}`);
								return r.json();
							})
							.then((d) => d.rutas ?? d)
					: Promise.resolve({});

			const indeterminadosPromise: Promise<any> = apiData.indeterminados
				? Promise.resolve(apiData.indeterminados)
				: apiData.indeterminadosUrl
					? fetch(apiData.indeterminadosUrl)
							.then((r) => {
								if (!r.ok) throw new Error(`Error al obtener indeterminados: ${r.statusText}`);
								return r.json();
							})
							.then((d) => d.indeterminados ?? d)
					: Promise.resolve({});

			const [rutasData, indeterminadosData] = await Promise.all([
				rutasPromise,
				indeterminadosPromise
			]);

			rutas = rutasData;
			indeterminados = indeterminadosData;

			sortedIndeterminados = Object.entries(indeterminados).sort(([, a], [, b]) => {
				const aIsEntradaConocida = a.labels[0] !== 'IND' && a.labels[1] === 'IND';
				const bIsEntradaConocida = b.labels[0] !== 'IND' && b.labels[1] === 'IND';
				if (aIsEntradaConocida && !bIsEntradaConocida) return -1;
				if (!aIsEntradaConocida && bIsEntradaConocida) return 1;
				return parseInt(a.frame) - parseInt(b.frame);
			});
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
		window.addEventListener('resize', updateVideoDimensions);
		return () => {
			window.removeEventListener('resize', updateVideoDimensions);
			stopAnimationLoop();
		};
	});
	function handleKeyPress(event: KeyboardEvent, trackId: string) {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			handleIndeterminateClick(trackId);
		}
	}
	function handleConfirm(trackId: string, event: MouseEvent) {
		event.stopPropagation();
		const item = indeterminados[trackId];
		if (!item) return;
		sortedIndeterminados = sortedIndeterminados.filter(([id]) => id !== trackId);
		if (activeBoundingBox === item.boundingBox) activeBoundingBox = null;
		playbackBoundingBoxes = playbackBoundingBoxes.filter((b) => b.id !== trackId);
		if (activeIndeterminateId === trackId) activeIndeterminateId = null;

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
		const item = indeterminados[trackId];
		sortedIndeterminados = sortedIndeterminados.filter(([id]) => id !== trackId);
		if (item && activeBoundingBox === item.boundingBox) activeBoundingBox = null;
		playbackBoundingBoxes = playbackBoundingBoxes.filter((b) => b.id !== trackId);
		if (activeIndeterminateId === trackId) activeIndeterminateId = null;

		delete indeterminados[trackId];
		indeterminados = { ...indeterminados };
		showNotification(`Vehículo indeterminado ${trackId} eliminado.`);
		updateBackendData();
	}
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
		<div class="flex flex-wrap justify-center items-start gap-8 mb-12">
			<!-- Reproductor de video -->
			<div class="w-full lg:w-2/3 max-w-5xl">
				{#if videoPath !== ''}
					<div
						class="relative rounded overflow-hidden border border-gray-600 bg-black aspect-video"
					>
						<video
							class="w-full h-full"
							controls
							autoplay
							bind:this={videoElement}
							onloadedmetadata={updateVideoDimensions}
							onplay={startAnimationLoop}
							onpause={stopAnimationLoop}
							onended={stopAnimationLoop}
							onseeking={() => {
								// Cuando el usuario arrastra el cursor, reseteamos el frame procesado
								// para que el bucle sepa que tiene que re-evaluar desde la nueva posición.
								if (videoElement) {
									lastProcessedFrame = Math.floor(videoElement.currentTime * videoFps) - 1;
								}
							}}
						>
							<source src={videoPath} type="video/mp4" />
							<track kind="captions" />
							Tu navegador no soporta la reproducción de video.
						</video>

						<!-- El bloque de renderizado de BBoxes no cambia -->
						{#each displayBoundingBoxes as box (box.id)}
							<div class="bbox-style" style={calculateBoxStyle(box)}>
								{#if box.id !== 'active-manual'}
									<div class="bbox-id-label">ID: {box.id}</div>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Lista de indeterminados -->
			{#if sortedIndeterminados.length > 0}
				<div
					class="w-full md:w-auto bg-[#2a2f3a] p-1 rounded-lg shadow-lg max-w-[450px] overflow-y-auto"
					style:height={videoHeightPx > 0 ? `${videoHeightPx}px` : 'auto'}
				>
					<h3 class="text-xl font-semibold mt-3 mb-3 text-center">Vehículos Indeterminados</h3>

					<div class="overflow-y-auto flex-1">
						<div class="space-y-3 p-1">
							{#each sortedIndeterminados as [trackId, item] (trackId)}
								{@const [entrada, salida] = item.labels}
								{@const canConfirm = entrada !== 'IND' && salida !== 'IND'}
								<div
									class="ind-card"
									class:live={liveIndeterminateIds.has(trackId) ||
										trackId === activeIndeterminateId}
									role="button"
									tabindex="0"
									onclick={() => handleIndeterminateClick(trackId)}
									onkeydown={(e) => handleKeyPress(e, trackId)}
								>
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
										class:bg-gray-500={!canConfirm && trackId !== activeIndeterminateId}
										class:bg-gray-300={trackId === activeIndeterminateId}
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
	.bbox-style {
		/* Borde blanco, 2px es un buen punto de partida */
		border: 2px solid #ffffff;

		/* Múltiples box-shadow para un efecto de neón más intenso.
		   Se apilan de atrás hacia adelante. */
		box-shadow:
			0 0 5px rgba(255, 255, 255, 0.8),
			/* Resplandor interior cercano */ 0 0 10px rgba(255, 255, 255, 0.6),
			/* Resplandor medio */ 0 0 20px rgba(255, 255, 255, 0.4); /* Resplandor exterior más difuso */

		pointer-events: none;
		z-index: 10;
		transition: transform 0.2s ease-in-out;
	}
	.ind-card {
		background-color: #383f4f;
		padding: 0.75rem;
		border-radius: 0.375rem;
		border: 2px solid #4a5568;
		cursor: pointer;
		transition:
			border-color 0.2s ease-in-out,
			box-shadow 0.2s ease-in-out,
			background-color 0.2s ease-in-out,
			color 0.2s ease-in-out;
		outline: none;
	}

	/* 1. Resplandor débil para hover (sin cambios) */
	.ind-card:hover {
		border-color: #a0aec0;
		box-shadow: 0 0 8px rgba(255, 255, 255, 0.2);
	}

	/* 2. Resplandor fuerte para la tarjeta "en vivo" durante la reproducción */
	.ind-card.live {
		transition: none;
		border-color: #ffffff;
		box-shadow:
			0 0 3px rgba(255, 255, 255, 0.5),
			0 0 7px rgba(255, 255, 255, 0.7);
	}

	/* 3. Estilo para la tarjeta seleccionada manualmente (la más importante) */
	.ind-card.selected {
		background-color: #ffffff;
		color: #1a1e2a; /* Color de texto por defecto para fondo blanco */
		border-color: #ffffff; /* Mantiene el borde blanco del glow */
		box-shadow: /* Mantiene el mismo glow fuerte */
			0 0 3px rgba(255, 255, 255, 0.5),
			0 0 7px rgba(255, 255, 255, 0.7);
	}

	/* --- Overrides para los elementos internos cuando la tarjeta está seleccionada --- */

	.ind-card.selected p,
	.ind-card.selected label {
		color: #1f2937; /* Texto principal oscuro */
	}

	.ind-card.selected .text-red-400 {
		color: #dc2626; /* Un rojo más oscuro y visible */
	}

	.ind-card.selected .text-red-400:hover {
		color: #b91c1c;
	}

	.ind-card.selected span.text-gray-400 {
		color: #4b5567; /* La flecha '→' */
	}

	.ind-card.selected select {
		background-color: #f3f4f6; /* Fondo gris claro para los selects */
		border-color: #9ca3af;
		color: #1f2937;
	}
	/* --- ESTILO AÑADIDO PARA LA ETIQUETA DEL ID DE LA BBOX --- */
	.bbox-id-label {
		/* Posicionamiento: arriba y a la izquierda de la BBox */
		position: absolute;
		bottom: 100%;
		left: -2px; /* Alineado con el borde de la BBox */
		margin-bottom: 5px; /* Pequeño espacio sobre la BBox */

		/* Estilo del contenedor para máxima legibilidad */
		background-color: rgba(0, 0, 0, 0.75); /* Fondo negro semitransparente */
		padding: 2px 8px;
		border-radius: 4px;

		/* Estilo del texto */
		color: white;
		font-family:
			system-ui,
			-apple-system,
			BlinkMacSystemFont,
			'Segoe UI',
			Roboto,
			Oxygen,
			Ubuntu,
			Cantarell,
			'Open Sans',
			'Helvetica Neue',
			sans-serif;
		font-size: 12px;
		font-weight: 600;
		white-space: nowrap; /* Evita que el ID se parta en dos líneas */

		/* Un suave resplandor al texto para que se integre mejor */
		text-shadow: 0 0 5px rgba(0, 0, 0, 0.9);
	}
</style>

<!-- src/routes/crear/+page.svelte -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	import { BACKEND_URL } from '$lib/constants';

	// Estado para el archivo seleccionado
	let selectedFile = $state<File | null>(null);

	// Estado para localidad y distrito
	let selectedLocality = $state('');
	let selectedDistrict = $state('');
	let selectedProvince = $state(1);

	// Datos de localidades y distritos
	let localities = $state<{ id: number; name: string }[]>([]);
	let districts = $state<{ id: number; name: string }[]>([]);
	let provinces = $state<{ id: number; name: string }[]>([]);

	async function fetchProvinces() {
		try {
			const response = await fetch(`${BACKEND_URL}/province`);
			if (!response.ok) {
				throw new Error(`Error fetching provinces: ${response.statusText}`);
			}
			provinces = await response.json();
		} catch (error) {
			console.error(error);
			alert('Error al cargar las provincias.');
		}
	}

	async function fetchDistricts() {
		try {
			const response = await fetch(`${BACKEND_URL}/province/1/district`);
			if (!response.ok) {
				throw new Error(`Error fetching districts: ${response.statusText}`);
			}
			districts = await response.json();
		} catch (error) {
			console.error(error);
			alert('Error al cargar los distritos.');
		}
	}

	async function fetchLocalities() {
		try {
			const response = await fetch(`${BACKEND_URL}/district/${selectedDistrict}/locality`);
			if (!response.ok) {
				throw new Error(`Error fetching localities: ${response.statusText}`);
			}
			localities = await response.json();
		} catch (error) {
			console.error(error);
			alert('Error al cargar las localidades.');
		}
	}

	$effect(() => {
		if (selectedProvince) {
			fetchDistricts();
		}
	});

	$effect(() => {
		if (selectedDistrict) {
			fetchLocalities();
		}
	});

	onMount(() => {
		fetchProvinces();
	});

	// Función para manejar la selección de archivos
	function handleFileSelect(event: Event): void {
		const input = event.target as HTMLInputElement;
		if (input.files && input.files.length > 0) {
			selectedFile = input.files[0];
		}
	}

	// Función para volver a la página anterior
	function goBack(): void {
		goto('/');
	}

	// Función para iniciar la subida
	async function handleSubmit(): Promise<void> {
		const fecha = (document.getElementById('fecha') as HTMLInputElement).value;
		const localidad = selectedLocality;
		const distritoId = selectedDistrict;
		const archivo = selectedFile;

		if (!fecha || !localidad || !distritoId || !archivo) {
			alert('Por favor complete todos los campos y seleccione un archivo.');
			return;
		}

		const formData = new FormData();
		const districtName =
			districts.find((d) => d.id.toString() === distritoId)?.name || 'Tarea sin nombre';

		formData.append('name', districtName);
		formData.append('locality_id', localidad); // El id de la localidad (string, backend espera int)
		formData.append('uploaded_at', fecha); // Fecha en formato YYYY-MM-DD
		formData.append('file', archivo);

		try {
			const response = await fetch(`${BACKEND_URL}/task`, {
				method: 'POST',
				body: formData
			});

			if (!response.ok) {
				const errorText = await response.text();
				throw new Error(`Error en la subida: ${errorText}`);
			}

			const data = await response.json();
			console.log('Tarea creada:', data);
			goto('/');
		} catch (error) {
			console.error('Error al crear la tarea:', error);
			alert('Hubo un error al crear la tarea.');
		}
	}
</script>

<div class="min-h-screen bg-[#1a1e2a] text-white p-6">
	<!-- Header con título y botón de volver -->
	<div class="max-w-3xl mx-auto mb-6 flex items-center">
		<button
			class="text-white mr-2 p-2 rounded-full hover:bg-gray-700 transition-colors"
			onclick={goBack}
			aria-label="Volver"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-6 w-6"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M10 19l-7-7m0 0l7-7m-7 7h18"
				/>
			</svg>
		</button>
		<h1 class="text-2xl font-bold">Crear Tarea</h1>
	</div>

	<!-- Formulario -->
	<div class="max-w-3xl mx-auto bg-[#12151c] rounded-lg p-8 border border-gray-700 shadow-lg">
		<h2 class="text-xl text-amber-400 text-center mb-8">Datos</h2>

		<form class="space-y-8">
			<!-- Campo Fecha simple -->
			<div class="flex flex-col space-y-2">
				<label for="fecha" class="text-lg">Fecha</label>
				<input
					type="date"
					id="fecha"
					class="bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
					value={new Date().toISOString().split('T')[0]}
				/>
				<div class="border-t border-gray-700 mt-2"></div>
			</div>

			<!-- Campos Localidad y Distrito (como selects independientes) -->
			<div class="flex flex-col space-y-6">
				<!-- Select de Provincia -->
				<div class="flex flex-col space-y-2">
					<label for="provincia" class="text-lg">Provincia</label>
					<select
						id="provincia"
						bind:value={selectedProvince}
						class="bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none"
					>
						<option value="" disabled selected>Seleccione una provincia</option>
						{#each provinces as province}
							<option value={province.id}>{province.name}</option>
						{/each}
					</select>
					<div class="border-t border-gray-700 mt-2"></div>
				</div>
				<!-- Select de Distrito -->
				<div class="flex flex-col space-y-2">
					<label for="distrito" class="text-lg">Distrito</label>
					<select
						id="distrito"
						bind:value={selectedDistrict}
						class="bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none"
					>
						<option value="" disabled selected>Seleccione un distrito</option>
						{#each districts as district}
							<option value={district.id}>{district.name}</option>
						{/each}
					</select>
					<div class="border-t border-gray-700 mt-2"></div>
				</div>
				<!-- Select de Localidad -->
				<div class="flex flex-col space-y-2">
					<label for="localidad" class="text-lg">Localidad</label>
					<select
						id="localidad"
						bind:value={selectedLocality}
						class="bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none"
					>
						<option value="" disabled selected>Seleccione una provincia</option>
						{#each localities as locality}
							<option value={locality.id}>{locality.name}</option>
						{/each}
					</select>
					<div class="border-t border-gray-700 mt-2"></div>
				</div>
			</div>

			<!-- Campo Archivo de video -->
			<div class="flex flex-col space-y-2">
				<label for="video" class="text-lg">Archivo de video</label>
				<div class="flex items-center space-x-4">
					<label
						for="video-upload"
						class="bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded flex items-center cursor-pointer"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="h-5 w-5 mr-2"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
							/>
						</svg>
						Seleccionar...
					</label>
					<input
						type="file"
						id="video-upload"
						accept=".mp4,.avi,.mov"
						class="hidden"
						onchange={handleFileSelect}
					/>
					<span class="text-gray-400">
						{selectedFile ? selectedFile.name : 'Ningún archivo seleccionado'}
					</span>
				</div>
				<p class="text-xs text-gray-400 mt-1">Formatos aceptados: MP4, AVI, MOV.</p>
				<div class="border-t border-gray-700 mt-2"></div>
			</div>

			<!-- Botón de envío -->
			<div class="flex justify-center mt-8">
				<button
					type="button"
					onclick={handleSubmit}
					class="bg-blue-600 hover:bg-blue-700 text-white py-3 px-8 rounded-md font-medium transition-colors"
				>
					Iniciar Subida
				</button>
			</div>
		</form>
	</div>
</div>

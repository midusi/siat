<!-- src/routes/crear/+page.svelte -->
<script lang="ts">
	import { goto } from '$app/navigation';

	// Estado para el archivo seleccionado
	let selectedFile = $state<File | null>(null);

	// Estado para localidad y distrito
	let selectedLocality = $state('');
	let selectedDistrict = $state('');

	// Datos de localidades y distritos
	const localities = [
		{ id: 'bsas', name: 'Buenos Aires' },
		{ id: 'cba', name: 'Córdoba' },
		{ id: 'stafe', name: 'Santa Fe' },
		{ id: 'mza', name: 'Mendoza' }
	];


	function
		try {
			const response = await fetch('http://127.0.0.1:8000/district' );

			if (!response.ok) {
			throw new Error(`Error en la petición: ${response.statusText}`);
			}

			const data = await response.json();
			console.log('Respuesta del backend:', data);

		} catch (error) {
			console.error('Error enviando los distritos:', error);
		}


	const districts = [
		{ id: 'lp', name: 'La Plata' },
		{ id: 'quilmes', name: 'Quilmes' },
		{ id: 'lomas', name: 'Lomas de Zamora' },
		{ id: 'moron', name: 'Morón' },
		{ id: 'capital', name: 'Capital' },
		{ id: 'vcp', name: 'Villa Carlos Paz' },
		{ id: 'rio4', name: 'Río Cuarto' },
		{ id: 'rosario', name: 'Rosario' },
		{ id: 'venado', name: 'Venado Tuerto' },
		{ id: 'godoy', name: 'Godoy Cruz' },
		{ id: 'lujan', name: 'Luján de Cuyo' }
	];

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
	function handleSubmit(): void {
		// Aquí iría la lógica para subir el archivo y crear la tarea
		console.log('Datos del formulario:', {
			fecha: (document.getElementById('fecha') as HTMLInputElement).value,
			localidad: selectedLocality,
			distrito: selectedDistrict,
			archivo: selectedFile
		});
		// Después de subir, redirigir a la página principal
		// goto('/');
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
					type="text"
					id="fecha"
					placeholder="DD/MM/AA"
					value="25/05/03"
					class="bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
				/>
				<div class="border-t border-gray-700 mt-2"></div>
			</div>

			<!-- Campos Localidad y Distrito (como selects independientes) -->
			<div class="flex flex-col space-y-6">
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
				<p class="text-xs text-gray-400 mt-1">Formatos aceptados: MP4, AVI, MOV. Máximo 300MB.</p>
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

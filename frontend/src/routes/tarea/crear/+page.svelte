<!-- src/routes/crear/+page.svelte -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import type { TaskForm } from '$lib/types/task';
	import { BACKEND_URL } from '$lib/constants';
	import { TaskFormSchema } from '$lib/types/task';
	import { z } from 'zod';

	// Estado agrupado en un objeto form
	let form = $state<TaskForm>({
		name: '',
		date: new Date().toISOString().split('T')[0],
		selectedProvince: 1,
		selectedDistrict: null as number | null,
		selectedLocality: null as number | null,
		file: null as File | null
	});

	let isFormValid = $state(false);
	let errors = $state<Record<string, string>>({});
	let submitted = $state(false);

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
			const response = await fetch(`${BACKEND_URL}/province/${form.selectedProvince}/district`);
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
			const response = await fetch(`${BACKEND_URL}/district/${form.selectedDistrict}/locality`);
			if (!response.ok) {
				throw new Error(`Error fetching localities: ${response.statusText}`);
			}
			localities = await response.json();
		} catch (error) {
			console.error(error);
			alert('Error al cargar las localidades.');
		}
	}

	// Función para manejar la selección de archivos
	function handleFileSelect(event: Event): void {
		const input = event.target as HTMLInputElement;
		if (input.files && input.files.length > 0) {
			const file = input.files[0];
			const allowedExtensions = ['.mp4', '.avi', '.mov'];
			const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
			if (!allowedExtensions.includes(ext)) {
				alert('El archivo debe ser .mp4, .avi o .mov');
				form.file = null;
				input.value = '';
				return;
			}
			form.file = file;
		}
	}

	// Función para iniciar la subida
	async function handleSubmit(): Promise<void> {
		submitted = true;
		const result = TaskFormSchema.safeParse(form);
		if (!result.success) {
			errors = {};
			for (const err of result.error.issues) {
				errors[String(err.path[0])] = err.message;
			}
			return;
		}
		errors = {};

		const formData = new FormData();
		formData.append('name', form.name);
		formData.append('locality_id', form.selectedLocality?.toString() ?? '');
		formData.append('date', form.date);
		if (form.file) {
			formData.append('file', form.file);
		}

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

	$effect(() => {
		if (form.selectedProvince) {
			fetchDistricts();
		}
	});

	$effect(() => {
		if (form.selectedDistrict) {
			fetchLocalities();
		}
	});

	$effect(() => {
		isFormValid = TaskFormSchema.safeParse(form).success;
		// console.log(isFormValid, form);
	});

	onMount(() => {
		fetchProvinces();
	});

	// Función para volver a la página anterior
	function goBack(): void {
		goto('/');
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
			<!-- Campo Nombre -->
			<div class="flex flex-col space-y-2">
				<label for="nombre" class="text-lg">Nombre *</label>
				<input
					type="text"
					id="nombre"
					class="bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
					bind:value={form.name}
					placeholder="Ingrese el nombre de la tarea"
				/>
				{#if submitted && errors.name}
					<span class="text-red-400 text-xs">{errors.name}</span>
				{/if}
				<div class="border-t border-gray-700 mt-2"></div>
			</div>
			<!-- Campo Fecha simple -->
			<div class="flex flex-col space-y-2">
				<label for="fecha" class="text-lg">Fecha *</label>
				<input
					type="date"
					id="fecha"
					class="bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
					bind:value={form.date}
					max={new Date().toISOString().split('T')[0]}
				/>
				{#if submitted && errors.date}
					<span class="text-red-400 text-xs">{errors.date}</span>
				{/if}
				<div class="border-t border-gray-700 mt-2"></div>
			</div>

			<!-- Campos Localidad y Distrito (como selects independientes) -->
			<div class="flex flex-col space-y-6">
				<!-- Select de Provincia -->
				<div class="flex flex-col space-y-2">
					<label for="provincia" class="text-lg">Provincia *</label>
					<select
						id="provincia"
						bind:value={form.selectedProvince}
						class="bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none"
					>
						<option value="" disabled selected>Seleccione una provincia</option>
						{#each provinces as province}
							<option value={province.id}>{province.name}</option>
						{/each}
					</select>
					{#if submitted && errors.selectedProvince}
						<span class="text-red-400 text-xs">{errors.selectedProvince}</span>
					{/if}
					<div class="border-t border-gray-700 mt-2"></div>
				</div>
				<!-- Select de Distrito -->
				<div class="flex flex-col space-y-2">
					<label for="distrito" class="text-lg">Distrito *</label>
					<select
						id="distrito"
						bind:value={form.selectedDistrict}
						class="bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none"
					>
						<option value={null} disabled selected>Seleccione un distrito</option>
						{#each districts as district}
							<option value={district.id}>{district.name}</option>
						{/each}
					</select>
					{#if submitted && errors.selectedDistrict}
						<span class="text-red-400 text-xs">{errors.selectedDistrict}</span>
					{/if}
					<div class="border-t border-gray-700 mt-2"></div>
				</div>
				<!-- Select de Localidad -->
				<div class="flex flex-col space-y-2">
					<label for="localidad" class="text-lg">Localidad *</label>
					<select
						id="localidad"
						bind:value={form.selectedLocality}
						class="bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none"
					>
						<option value={null} disabled selected>
							Seleccione {form.selectedDistrict === null ? 'un distrito' : 'una localidad'}
						</option>
						{#each localities as locality}
							<option value={locality.id}>{locality.name}</option>
						{/each}
					</select>
					{#if submitted && errors.selectedLocality}
						<span class="text-red-400 text-xs">{errors.selectedLocality}</span>
					{/if}
					<div class="border-t border-gray-700 mt-2"></div>
				</div>
			</div>

			<!-- Campo Archivo de video -->
			<div class="flex flex-col space-y-2">
				<label for="video" class="text-lg">Archivo de video *</label>
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
						{form.file ? form.file.name : 'Ningún archivo seleccionado'}
					</span>
					{#if submitted && errors.file}
						<span class="text-red-400 text-xs">{errors.file}</span>
					{/if}
				</div>
				<p class="text-xs text-gray-400 mt-1">Formatos aceptados: MP4, AVI, MOV.</p>
				<div class="border-t border-gray-700 mt-2"></div>
			</div>

			<!-- Botón de envío -->
			<div class="flex justify-center mt-8">
				<button
					type="button"
					onclick={handleSubmit}
					class="py-3 px-8 rounded-md font-medium transition-colors
						{!isFormValid
						? 'bg-gray-500 text-gray-300 cursor-not-allowed'
						: 'bg-blue-600 hover:bg-blue-700 text-white'}"
					disabled={!isFormValid}
				>
					Crear Tarea
				</button>
			</div>
		</form>
	</div>
</div>

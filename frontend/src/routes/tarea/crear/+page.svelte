<!-- src/routes/crear/+page.svelte -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import type { TaskForm } from '$lib/types/task';
	import { BACKEND_URL } from '$lib/constants';
	import { TaskFormSchema } from '$lib/types/task';
	import { z } from 'zod';
	import { showAlert } from '$lib/dialog';
	import Spinner from '$lib/components/Spinner.svelte';
	import GlassSelect from '$lib/components/GlassSelect.svelte';

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
	let isUploading = $state(false);
	let uploadProgress = $state(0); // 0-100
	let isProcessing = $state(false); // true cuando ya se subió y el backend está creando la tarea

	// Datos de localidades y distritos
	let localities = $state<{ id: number; name: string }[]>([]);
	let districts = $state<{ id: number; name: string }[]>([]);
	let provinces = $state<{ id: number; name: string }[]>([]);

	async function fetchProvinces() {
		try {
			const response = await fetch(`${BACKEND_URL}/province`, { credentials: 'include' });
			if (!response.ok) {
				throw new Error(`Error fetching provinces: ${response.statusText}`);
			}
			provinces = await response.json();
		} catch (error) {
			console.error(error);
			await showAlert({ message: 'Error al cargar las provincias.', variant: 'danger' });
		}
	}

	async function fetchDistricts() {
		try {
			const response = await fetch(`${BACKEND_URL}/province/${form.selectedProvince}/district`, {
				credentials: 'include'
			});
			if (!response.ok) {
				throw new Error(`Error fetching districts: ${response.statusText}`);
			}
			districts = await response.json();
		} catch (error) {
			console.error(error);
			await showAlert({ message: 'Error al cargar los distritos.', variant: 'danger' });
		}
	}

	async function fetchLocalities() {
		try {
			const response = await fetch(`${BACKEND_URL}/district/${form.selectedDistrict}/locality`, {
				credentials: 'include'
			});
			if (!response.ok) {
				throw new Error(`Error fetching localities: ${response.statusText}`);
			}
			localities = await response.json();
		} catch (error) {
			console.error(error);
			await showAlert({ message: 'Error al cargar las localidades.', variant: 'danger' });
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
				showAlert({ message: 'El archivo debe ser .mp4, .avi o .mov', variant: 'warning' });
				form.file = null;
				input.value = '';
				return;
			}
			form.file = file;
		}
	}

	// Función para iniciar la subida
	async function handleSubmit(): Promise<void> {
		if (isUploading) return; // evitar envíos duplicados
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

		isUploading = true;
		isProcessing = false;

		const formData = new FormData();
		formData.append('name', form.name);
		formData.append('locality_id', form.selectedLocality?.toString() ?? '');
		formData.append('date', form.date);
		if (form.file) {
			formData.append('file', form.file);
		}

		try {
			const data = await new Promise<any>((resolve, reject) => {
				const xhr = new XMLHttpRequest();
				xhr.open('POST', `${BACKEND_URL}/task`, true);
				xhr.withCredentials = true;
				xhr.upload.onprogress = (event: ProgressEvent<EventTarget>) => {
					if (event.lengthComputable) {
						uploadProgress = Math.round((event.loaded / event.total) * 100);
					}
				};
				xhr.upload.onload = () => {
					// Subida terminada, ahora el servidor procesa la creación de la tarea
					uploadProgress = 100;
					isProcessing = true;
				};
				xhr.upload.onerror = () => {
					reject(new Error('Error durante la subida del archivo'));
				};
				xhr.onload = () => {
					if (xhr.status >= 200 && xhr.status < 300) {
						try {
							const json = JSON.parse(xhr.responseText || '{}');
							resolve(json);
						} catch (e) {
							resolve({});
						}
					} else {
						reject(new Error(`Error en la subida: ${xhr.status} ${xhr.responseText}`));
					}
				};
				xhr.onerror = () => reject(new Error('Error de red durante la subida'));
				xhr.send(formData);
			});

			console.log('Tarea creada:', data);
			goto('/');
		} catch (error) {
			console.error('Error al crear la tarea:', error);
			await showAlert({ message: 'Hubo un error al crear la tarea.', variant: 'danger' });
		} finally {
			isUploading = false;
			isProcessing = false;
			uploadProgress = 0;
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

<div class="page-container">
	<!-- Header con título y botón de volver -->
	<div class="max-w-3xl mx-auto mb-6 flex items-center gap-2">
		<button
			class="glass-button p-2 text-white/90 hover:text-white border border-white/20 bg-white/10 hover:bg-white/20"
			onclick={goBack}
			aria-label="Volver"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-5 w-5"
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
		<h1 class="heading-1">Crear Tarea</h1>
	</div>

	<!-- Formulario -->
	<div class="max-w-3xl mx-auto glass-card p-6 sm:p-8">
		<h2 class="heading-2 text-center mb-8">Datos</h2>

		<form class="space-y-8">
			<!-- Campo Nombre -->
			<div class="flex flex-col space-y-2">
				<label for="nombre" class="text-lg">Nombre *</label>
				<input
					type="text"
					id="nombre"
					class="glass-input"
					bind:value={form.name}
					placeholder="Ingrese el nombre de la tarea"
				/>
				{#if submitted && errors.name}
					<span class="text-red-300/90 text-xs">{errors.name}</span>
				{/if}
				<div class="border-t glass-divider mt-2"></div>
			</div>
			<!-- Campo Fecha simple -->
			<div class="flex flex-col space-y-2">
				<label for="fecha" class="text-lg">Fecha *</label>
				<input
					type="date"
					id="fecha"
					class="glass-input"
					bind:value={form.date}
					max={new Date().toISOString().split('T')[0]}
				/>
				{#if submitted && errors.date}
					<span class="text-red-300/90 text-xs">{errors.date}</span>
				{/if}
				<div class="border-t glass-divider mt-2"></div>
			</div>

			<!-- Campos Localidad y Distrito (como selects independientes) -->
			<div class="flex flex-col space-y-6">
				<!-- Select de Provincia -->
				<div class="flex flex-col space-y-2">
					<label for="provincia" class="text-lg">Provincia *</label>
					<GlassSelect
						id="provincia"
						ariaLabel="Provincia"
						items={provinces.map((p) => ({ value: p.id, label: p.name }))}
						value={form.selectedProvince}
						onChange={(v) => {
							form.selectedProvince = Number(v);
							form.selectedDistrict = null;
							form.selectedLocality = null;
						}}
					/>
					{#if submitted && errors.selectedProvince}
						<span class="text-red-300/90 text-xs">{errors.selectedProvince}</span>
					{/if}
					<div class="border-t glass-divider mt-2"></div>
				</div>
				<!-- Select de Distrito -->
				<div class="flex flex-col space-y-2">
					<label for="distrito" class="text-lg">Distrito *</label>
					<GlassSelect
						id="distrito"
						ariaLabel="Distrito"
						items={districts.map((d) => ({ value: d.id, label: d.name }))}
						value={form.selectedDistrict}
						onChange={(v) => {
							form.selectedDistrict = v === null ? null : Number(v);
							form.selectedLocality = null;
						}}
					/>
					{#if submitted && errors.selectedDistrict}
						<span class="text-red-300/90 text-xs">{errors.selectedDistrict}</span>
					{/if}
					<div class="border-t glass-divider mt-2"></div>
				</div>
				<!-- Select de Localidad -->
				<div class="flex flex-col space-y-2">
					<label for="localidad" class="text-lg">Localidad *</label>
					<GlassSelect
						id="localidad"
						ariaLabel="Localidad"
						items={localities.map((l) => ({ value: l.id, label: l.name }))}
						value={form.selectedLocality}
						onChange={(v) => {
							form.selectedLocality = v === null ? null : Number(v);
						}}
					/>
					{#if submitted && errors.selectedLocality}
						<span class="text-red-300/90 text-xs">{errors.selectedLocality}</span>
					{/if}
					<div class="border-t glass-divider mt-2"></div>
				</div>
			</div>

			<!-- Campo Archivo de video -->
			<div class="flex flex-col space-y-2">
				<label for="video" class="text-lg">Archivo de video *</label>
				<div class="flex items-center space-x-4">
					<label
						for="video-upload"
						class="glass-button cursor-pointer px-4 py-2 border-sky-400/40 bg-sky-300/12 hover:bg-sky-300/20 text-sky-100 flex items-center"
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
					<span class="text-white/80">
						{form.file ? form.file.name : 'Ningún archivo seleccionado'}
					</span>
					{#if submitted && errors.file}
						<span class="text-red-300/90 text-xs">{errors.file}</span>
					{/if}
				</div>
				<p class="text-xs text-white/70 mt-1">Formatos aceptados: MP4, AVI, MOV.</p>
				<div class="border-t glass-divider mt-2"></div>
			</div>

			<!-- Botón de envío -->
			<div class="flex justify-center mt-8">
				<button
					type="button"
					onclick={handleSubmit}
					class="relative overflow-hidden glass-button px-6 py-3 w-56 justify-center text-center
						{!isUploading && isFormValid
						? 'border-indigo-300/30 bg-indigo-300/12 hover:bg-indigo-300/20 text-indigo-100'
						: ''}
						{isUploading ? 'cursor-not-allowed' : ''}"
					aria-busy={isUploading}
					aria-disabled={isUploading || !isFormValid}
					role={isUploading && !isProcessing ? 'progressbar' : undefined}
					aria-valuemin={isUploading && !isProcessing ? 0 : undefined}
					aria-valuemax={isUploading && !isProcessing ? 100 : undefined}
					aria-valuenow={isUploading && !isProcessing ? uploadProgress : undefined}
					disabled={!isFormValid || isUploading}
				>
					{#if isUploading}
						<!-- Barra de progreso como background -->
						<div class="absolute inset-0 bg-white/5"></div>
						<div
							class="absolute inset-y-0 left-0 transition-[width] duration-150"
							style="width: {isProcessing
								? 100
								: uploadProgress}%; background: linear-gradient(to right, rgba(129,140,248,0.25), rgba(226,232,240,0.15));"
						></div>
						<span class="relative z-10 inline-flex items-center gap-2">
							{#if !isProcessing}
								Subiendo video {uploadProgress}%
							{:else}
								<Spinner size={16} />
								Creando tarea...
							{/if}
						</span>
					{:else}
						Crear Tarea
					{/if}
				</button>
			</div>
		</form>
	</div>
</div>

<script lang="ts">
	import {
		ALLOWED_VIDEO_EXTENSIONS,
		INVALID_VIDEO_MESSAGE,
		isAllowedVideo,
		TaskFormSchema
	} from '$lib/validation/task';
	import { createTask } from '$lib/services/tasks';
	import { errorMessage } from '$lib/services/errors';
	import {
		fetchDistricts,
		fetchLocalities,
		fetchProvinces,
		toSelectItems
	} from '$lib/services/locations';
	import FormRow from '$lib/components/FormRow.svelte';
	import GlassSelect from '$lib/components/GlassSelect.svelte';
	import { goto } from '$app/navigation';
	import Icon from '$lib/components/Icon.svelte';
	import { localDateString } from '$lib/format';
	import { onMount } from 'svelte';
	import { showAlert } from '$lib/dialog.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import { uploadVideoToMinio } from '$lib/services/upload';

	import type { Option, SelectItem } from '$lib/services/locations';
	import type { TaskForm } from '$lib/validation/task';

	type TaskValidation = ReturnType<typeof TaskFormSchema.safeParse>;

	const ACCEPTED_FORMATS: string = ALLOWED_VIDEO_EXTENSIONS.map((ext) =>
		ext.slice(1).toUpperCase()
	).join(', ');

	let districts: Array<Option> = $state([]);
	let form: TaskForm = $state({
		name: '',
		date: localDateString(),
		selectedProvince: 1,
		selectedDistrict: null,
		selectedLocality: null,
		file: null
	});
	let isProcessing: boolean = $state(false);
	let isUploading: boolean = $state(false);
	let localities: Array<Option> = $state([]);
	let provinces: Array<Option> = $state([]);
	let submitted: boolean = $state(false);
	let uploadProgress: number = $state(0);

	const validation: TaskValidation = $derived(TaskFormSchema.safeParse(form));
	const districtItems: Array<SelectItem> = $derived(toSelectItems(districts));
	const errors: Record<string, string> = $derived(
		submitted && !validation.success
			? Object.fromEntries(
					validation.error.issues.map((i) => [String(i.path[0]), i.message] as const)
				)
			: {}
	);
	const isFormValid: boolean = $derived(validation.success);
	const localityItems: Array<SelectItem> = $derived(toSelectItems(localities));
	const provinceItems: Array<SelectItem> = $derived(toSelectItems(provinces));

	$effect(() => {
		if (form.selectedProvince) {
			getDistricts();
		} else {
			districts = [];
		}
	});

	$effect(() => {
		if (form.selectedDistrict) {
			getLocalities();
		} else {
			localities = [];
		}
	});

	onMount(() => {
		getProvinces();
	});

	const loadOptions = async (request: () => Promise<Array<Option>>): Promise<Array<Option>> => {
		try {
			return await request();
		} catch (e) {
			await showAlert({ message: errorMessage(e), variant: 'danger' });
			return [];
		}
	};

	const getDistricts = async (): Promise<void> => {
		districts = await loadOptions(() => fetchDistricts(form.selectedProvince!));
	};

	const getLocalities = async (): Promise<void> => {
		localities = await loadOptions(() => fetchLocalities(form.selectedDistrict!));
	};

	const getProvinces = async (): Promise<void> => {
		provinces = await loadOptions(fetchProvinces);
	};

	const handleFileSelect = (event: Event): void => {
		const input: HTMLInputElement = event.target as HTMLInputElement;
		const file: File | undefined = input.files?.[0];
		if (!file) {
			return;
		}
		if (!isAllowedVideo(file)) {
			showAlert({ message: INVALID_VIDEO_MESSAGE, variant: 'warning' });
			form.file = null;
			input.value = '';
			return;
		}
		form.file = file;
	};

	const handleSubmit = async (event: SubmitEvent): Promise<void> => {
		event.preventDefault();
		if (isUploading) {
			return;
		}
		submitted = true;
		if (!isFormValid || !form.file) {
			return;
		}
		isUploading = true;
		try {
			const objectKey: string = await uploadVideoToMinio(
				form.file,
				(p) => (uploadProgress = p.percentage)
			);
			isProcessing = true;
			await createTask({
				name: form.name,
				localityId: form.selectedLocality!,
				date: form.date,
				objectKey
			});
			await showAlert({ message: 'Tarea creada exitosamente', variant: 'success' });
			goto('/');
		} catch (e) {
			console.error('Error al crear la tarea:', e);
			await showAlert({
				message: errorMessage(e, 'Hubo un error al crear la tarea.'),
				variant: 'danger'
			});
		} finally {
			isUploading = false;
			isProcessing = false;
			uploadProgress = 0;
		}
	};
</script>

<div class="page-container">
	<div class="max-w-3xl mx-auto mb-6 flex items-center gap-2">
		<a
			href="/"
			class="glass-button p-2 text-white/90 hover:text-white border border-white/20 bg-white/10 hover:bg-white/20"
			aria-label="Volver"
		>
			<Icon name="arrow-left" />
		</a>
		<h1 class="heading-1">Crear Tarea</h1>
	</div>

	<div class="max-w-3xl mx-auto glass-card p-6 sm:p-8">
		<h2 class="heading-2 text-center mb-8">Datos</h2>

		<form class="space-y-8" onsubmit={handleSubmit}>
			<FormRow label="Nombre *" for="nombre" error={errors.name}>
				<input
					type="text"
					id="nombre"
					class="glass-input"
					bind:value={form.name}
					placeholder="Ingrese el nombre de la tarea"
				/>
			</FormRow>

			<FormRow label="Fecha *" for="fecha" error={errors.date}>
				<input
					type="date"
					id="fecha"
					class="glass-input"
					bind:value={form.date}
					max={localDateString()}
				/>
			</FormRow>

			<div class="flex flex-col space-y-6">
				<FormRow label="Provincia *" for="provincia" error={errors.selectedProvince}>
					<GlassSelect
						id="provincia"
						ariaLabel="Provincia"
						items={provinceItems}
						value={form.selectedProvince}
						onChange={(v) => {
							form.selectedProvince = v === null ? null : Number(v);
							form.selectedDistrict = null;
							form.selectedLocality = null;
						}}
					/>
				</FormRow>

				<FormRow label="Distrito *" for="distrito" error={errors.selectedDistrict}>
					<GlassSelect
						id="distrito"
						ariaLabel="Distrito"
						items={districtItems}
						value={form.selectedDistrict}
						onChange={(v) => {
							form.selectedDistrict = v === null ? null : Number(v);
							form.selectedLocality = null;
						}}
					/>
				</FormRow>

				<FormRow label="Localidad *" for="localidad" error={errors.selectedLocality}>
					<GlassSelect
						id="localidad"
						ariaLabel="Localidad"
						items={localityItems}
						value={form.selectedLocality}
						onChange={(v) => {
							form.selectedLocality = v === null ? null : Number(v);
						}}
					/>
				</FormRow>
			</div>

			<FormRow label="Archivo de video *" for="video-upload" error={errors.file}>
				<div class="flex items-center space-x-4">
					<label
						for="video-upload"
						class="glass-button cursor-pointer px-4 py-2 border-sky-400/40 bg-sky-300/12 hover:bg-sky-300/20 text-sky-100 flex items-center"
					>
						<Icon name="upload" class="h-5 w-5 mr-2" />
						Seleccionar...
					</label>
					<input
						type="file"
						id="video-upload"
						accept={ALLOWED_VIDEO_EXTENSIONS.join(',')}
						class="hidden"
						onchange={handleFileSelect}
					/>
					<span class="text-white/80">
						{form.file ? form.file.name : 'Ningún archivo seleccionado'}
					</span>
				</div>
				<p class="text-xs text-white/70 mt-1">Formatos aceptados: {ACCEPTED_FORMATS}.</p>
			</FormRow>

			<div class="flex justify-center mt-8">
				<button
					type="submit"
					class={[
						'relative overflow-hidden glass-button px-6 py-3 w-56 justify-center text-center',
						!isUploading &&
							isFormValid &&
							'border-indigo-300/30 bg-indigo-300/12 hover:bg-indigo-300/20 text-indigo-100'
					]}
					aria-busy={isUploading}
					disabled={isUploading}
				>
					{#if isUploading}
						<div class="absolute inset-0 bg-white/5"></div>
						<div
							class="absolute inset-y-0 left-0 transition-[width] duration-150"
							role={isProcessing ? undefined : 'progressbar'}
							aria-label={isProcessing ? undefined : 'Progreso de subida'}
							aria-valuemin={isProcessing ? undefined : 0}
							aria-valuemax={isProcessing ? undefined : 100}
							aria-valuenow={isProcessing ? undefined : uploadProgress}
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

<script lang="ts">
	import { errorMessage } from '$lib/services/errors';
	import { getCategoryColor } from '$lib/colors';
	import IndeterminadosPanel from './IndeterminadosPanel.svelte';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import ResumenTablas from './ResumenTablas.svelte';
	import * as review from './review';
	import { showError, showSuccess } from '$lib/toast';
	import Spinner from '$lib/components/Spinner.svelte';
	import VideoPanel from './VideoPanel.svelte';

	let activeIndeterminateId: string | null = $state(null);
	let determinados: review.Indeterminados = $state({});
	let error: string | null = $state(null);
	let excludedZones: Array<Array<review.Vertex>> = $state([]);
	let generalReady: boolean = $state(false);
	let history: review.History = $state({});
	let indeterminados: review.Indeterminados = $state({});
	let liveIds: Set<string> = $state(new Set());
	let loading: boolean = $state(true);
	let mergeInProgress: boolean = $state(false);
	let roadsIn: Array<review.RoadPoly> = $state([]);
	let roadsOut: Array<review.RoadPoly> = $state([]);
	let rutas: review.Rutas = $state({});
	let savingById: Record<string, boolean> = $state({});
	let sortedIndeterminados: Array<[string, review.Indeterminado]> = $state([]);
	let trackHistory: review.TrackHistory = $state.raw(new Map());
	let videoFps: number = $state(0);
	let videoHeight: number = $state(0);
	let videoPanel: VideoPanel | null = $state(null);
	let videoPanelHeight: number = $state(0);
	let videoPath: string = $state('');
	let videoWidth: number = $state(0);

	const hasRutas: boolean = $derived(Object.keys(rutas).length > 0);
	const taskId: string = $derived(page.params.id);
	const vehicleTypes: Array<string> = $derived(review.getVehicleTypes(rutas, indeterminados));
	const vehicleItems: Array<review.SelectOption> = $derived(
		vehicleTypes.map((v) => ({ value: v, label: review.getVehicleName(v) }))
	);
	const zoneItems: Array<review.SelectOption> = $derived([
		{ value: '', label: 'Seleccionar…' },
		...review.getZoneIds(rutas).map((z) => ({ value: z, label: `Zona ${z}` }))
	]);

	onMount(() => {
		fetchData();
	});

	const loadTrackHistory = async (url: string | null): Promise<void> => {
		let tracks: review.TrackHistory = new Map();
		if (url) {
			try {
				tracks = await review.fetchTrackHistory(url);
			} catch (e) {
				console.error(e);
			}
		}
		trackHistory = tracks;
		generalReady = true;
	};

	const fetchData = async (): Promise<void> => {
		loading = true;
		error = null;
		generalReady = false;
		try {
			const data: review.TaskReview = await review.fetchTaskReview(taskId);
			videoPath = data.videoPath;
			videoWidth = data.videoWidth;
			videoHeight = data.videoHeight;
			videoFps = data.videoFps;
			roadsIn = data.roadsIn;
			roadsOut = data.roadsOut;
			excludedZones = data.excludedZones;
			rutas = data.rutas;
			indeterminados = data.indeterminados;
			determinados = data.determinados;
			history = data.history;
			sortedIndeterminados = review.sortIndeterminados(indeterminados);
			loadTrackHistory(data.historyUrl);
		} catch (e) {
			error = errorMessage(e, 'Error desconocido al cargar los datos.');
		} finally {
			loading = false;
		}
	};

	const saveChanges = async (): Promise<boolean> => {
		try {
			await review.updateTaskReview(taskId, {
				rutas,
				indeterminados,
				determinados,
				trackHistory
			});
			return true;
		} catch (e) {
			showError(errorMessage(e, 'No se pudo guardar los cambios en el servidor.'));
			await fetchData();
			return false;
		}
	};

	const updateTracks = (change: (tracks: review.TrackHistory) => void): void => {
		const next: review.TrackHistory = new Map(trackHistory);
		change(next);
		trackHistory = next;
	};

	const classColor = (cls: string): string => getCategoryColor(cls, vehicleTypes);

	const trackColor = (trackId: string): string => {
		const cls: string | null = review.getTrackClass(trackId, determinados, indeterminados, history);
		return cls ? classColor(cls) : '#ffffff';
	};

	const hideIndeterminado = (trackId: string): void => {
		sortedIndeterminados = sortedIndeterminados.filter(([id]) => id !== trackId);
		if (activeIndeterminateId === trackId) {
			activeIndeterminateId = null;
		}
	};

	const moveToDeterminados = (trackId: string, entrada: string, salida: string): void => {
		const item: review.Indeterminado = indeterminados[trackId];
		review.incrementarRuta(rutas, entrada, salida, item.class, vehicleTypes);
		determinados[trackId] = { ...item, labels: { in: entrada, out: salida } };
		delete indeterminados[trackId];
	};

	const selectIndeterminado = (trackId: string): void => {
		activeIndeterminateId = trackId;
		const item: review.Indeterminado | undefined = indeterminados[trackId];
		if (item) {
			videoPanel?.focusTrack(trackId, parseInt(item.first_appearance.frame));
		}
	};

	const onBBoxClick = (trackId: string): void => {
		if (!indeterminados[trackId]) {
			return;
		}
		activeIndeterminateId = trackId;
		queueMicrotask(() => {
			const el: HTMLElement | null = document.getElementById(`ind-card-${trackId}`);
			if (el) {
				el.scrollIntoView({ behavior: 'smooth', block: 'center' });
				el.focus({ preventScroll: true });
			}
		});
	};

	const editIndeterminado = (
		trackId: string,
		field: review.IndeterminadoField,
		value: string
	): void => {
		const item: review.Indeterminado | undefined = indeterminados[trackId];
		if (!item) {
			return;
		}
		if (field === 'class') {
			item.class = value;
		} else {
			item.labels[field] = value;
		}
	};

	const confirmIndeterminado = async (trackId: string): Promise<void> => {
		const item: review.Indeterminado | undefined = indeterminados[trackId];
		if (!item) {
			return;
		}
		savingById[trackId] = true;
		hideIndeterminado(trackId);

		const { in: entrada, out: salida }: review.Labels = item.labels;
		moveToDeterminados(trackId, entrada, salida);

		if (await saveChanges()) {
			showSuccess(`Vehículo ${trackId} confirmado y añadido a la ruta ${entrada} -> ${salida}.`);
		}
		delete savingById[trackId];
	};

	const deleteIndeterminado = async (trackId: string): Promise<void> => {
		savingById[trackId] = true;
		hideIndeterminado(trackId);
		videoPanel?.retargetSelection(trackId, null);
		if (trackHistory.has(trackId)) {
			updateTracks((tracks) => tracks.delete(trackId));
		}
		delete indeterminados[trackId];

		if (await saveChanges()) {
			showSuccess(`Vehículo indeterminado ${trackId} eliminado.`);
		}
		delete savingById[trackId];
	};

	const mergeIndeterminados = async (keepId: string, removeId: string): Promise<void> => {
		if (mergeInProgress) {
			return;
		}
		mergeInProgress = true;
		try {
			const keep: review.Indeterminado | undefined = indeterminados[keepId];
			const remove: review.Indeterminado | undefined = indeterminados[removeId];
			if (!keep || !remove) {
				showError('No se encontraron ambos indeterminados.');
				return;
			}

			const merged: review.Indeterminado = review.mergeIndeterminados(keep, remove);
			const { in: entrada, out: salida }: review.Labels = merged.labels;
			indeterminados[keepId] = merged;
			delete indeterminados[removeId];

			hideIndeterminado(removeId);
			videoPanel?.retargetSelection(removeId, keepId);
			updateTracks((tracks) => {
				tracks.set(
					keepId,
					review.mergeTrackPoints(tracks.get(keepId) ?? [], tracks.get(removeId) ?? [])
				);
				tracks.delete(removeId);
			});

			const nowDetermined: boolean =
				!review.isUnknownLabel(entrada) && !review.isUnknownLabel(salida);
			if (nowDetermined) {
				moveToDeterminados(keepId, entrada, salida);
			}
			sortedIndeterminados = review.sortIndeterminados(indeterminados);

			if (!(await saveChanges())) {
				return;
			}
			if (nowDetermined) {
				showSuccess(
					`Indeterminados ${keepId} y ${removeId} unidos y confirmado ${keepId} como ${entrada} → ${salida}.`
				);
			} else {
				showSuccess(`Indeterminados ${keepId} y ${removeId} unidos (se conserva ${keepId}).`);
			}
		} finally {
			mergeInProgress = false;
		}
	};
</script>

<div class="min-h-screen py-8 px-4">
	<div class="max-w-7xl mx-auto mb-4">
		<h1 class="text-3xl font-bold text-center">Revisar Video Analizado</h1>
	</div>

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
		<div class="flex flex-col xl:flex-row justify-center items-center xl:items-start gap-8 mb-12">
			<div class="w-full xl:flex-1 xl:min-w-0 max-w-5xl">
				{#if videoPath !== '' && generalReady}
					<VideoPanel
						bind:this={videoPanel}
						bind:activeTrackId={activeIndeterminateId}
						bind:height={videoPanelHeight}
						bind:liveIds
						{videoPath}
						{videoFps}
						{videoWidth}
						{videoHeight}
						{roadsIn}
						{roadsOut}
						{excludedZones}
						{trackHistory}
						{indeterminados}
						{trackColor}
						onbboxclick={onBBoxClick}
					/>
				{:else}
					<div class="flex items-center justify-center w-full h-full min-h-[320px] bg-[#111]">
						<Spinner size={48} />
					</div>
				{/if}
			</div>

			{#if generalReady && videoPath !== '' && sortedIndeterminados.length > 0}
				<IndeterminadosPanel
					items={sortedIndeterminados}
					{vehicleItems}
					{zoneItems}
					{savingById}
					{mergeInProgress}
					{liveIds}
					activeId={activeIndeterminateId}
					height={videoPanelHeight}
					{classColor}
					onselect={selectIndeterminado}
					onedit={editIndeterminado}
					onconfirm={confirmIndeterminado}
					ondelete={deleteIndeterminado}
					onmerge={mergeIndeterminados}
				/>
			{/if}
		</div>

		{#if hasRutas}
			<ResumenTablas {rutas} {vehicleTypes} {classColor} />
		{/if}
	{/if}
</div>

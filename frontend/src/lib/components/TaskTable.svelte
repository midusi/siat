<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import SearchInput from '$lib/components/SearchInput.svelte';
	import Spinner from '$lib/components/Spinner.svelte';

	import type { ActionType, BusyActions, TaskRow } from '$lib/types/task';

	type Props = {
		busy?: BusyActions;
		loading?: boolean;
		onAction: (action: ActionType, id: number) => void;
		onRightButtonClick?: () => void;
		rightButtonLabel?: string;
		rows?: Array<TaskRow>;
		title: string;
	};

	const ACTION_STYLES: Record<ActionType, string> = {
		configurar: 'border-indigo-400/40 bg-indigo-300/12 hover:bg-indigo-300/20 text-indigo-100',
		revisar: 'border-sky-400/40 bg-sky-300/12 hover:bg-sky-300/20 text-sky-100',
		archivar: 'border-amber-400/40 bg-amber-300/12 hover:bg-amber-300/20 text-amber-100',
		eliminar: 'border-red-600/50 bg-red-600/15 hover:bg-red-600/25 text-red-100',
		desarchivar: 'border-green-500/40 bg-green-400/12 hover:bg-green-400/20 text-green-100'
	};

	const BUSY_LABELS: Partial<Record<ActionType, string>> = {
		archivar: 'Archivando...',
		desarchivar: 'Desarchivando...',
		eliminar: 'Eliminando...'
	};

	const COLUMNS: Array<string> = [
		'ID',
		'Fecha',
		'Nombre',
		'Localidad',
		'Estado',
		'Detalle',
		'Acciones'
	];

	let {
		busy = {},
		loading = false,
		onAction,
		onRightButtonClick,
		rightButtonLabel,
		rows = [],
		title
	}: Props = $props();

	let filter: string = $state('');

	const visibleRows: Array<TaskRow> = $derived.by((): Array<TaskRow> => {
		const query: string = filter.trim().toLowerCase();
		return rows
			.filter(
				(row: TaskRow): boolean =>
					row.nombre.toLowerCase().includes(query) || row.localidad.toLowerCase().includes(query)
			)
			.sort((a: TaskRow, b: TaskRow): number => b.id - a.id);
	});
</script>

<div class="h-full">
	<!-- Header -->
	<div class="glass-card px-4 py-3 mb-4 border glass-divider">
		<div class="flex justify-between items-center">
			<div class="flex items-center gap-2">
				<Icon name="document" class="h-6 w-6 text-blue-500" />
				<h1 class="heading-1" style="color: hsl(var(--foreground));">
					{title}
				</h1>
			</div>
			{#if rightButtonLabel && onRightButtonClick}
				<button onclick={onRightButtonClick} class="glass-button">
					{rightButtonLabel}
				</button>
			{/if}
		</div>
	</div>

	<!-- Filter -->
	<div class="page-container px-0">
		<SearchInput bind:value={filter} placeholder="Filtrar por nombre o localidad..." />
	</div>

	<!-- Table -->
	<div class="page-container px-0">
		<div class="glass-card border glass-divider overflow-x-auto">
			<table class="w-full border-collapse text-sm">
				<thead>
					<tr
						class="glass-surface"
						style="background-image: linear-gradient(0deg, hsl(var(--accent1) / 0.06), transparent);"
					>
						{#each COLUMNS as column (column)}
							<th class="p-3 text-left font-medium">{column}</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					{#if loading}
						<tr>
							<td colspan={COLUMNS.length} class="p-6 text-center opacity-80">Cargando...</td>
						</tr>
					{:else}
						{#each visibleRows as task (task.id)}
							{@const busyAction = busy[task.id]}
							<tr class="border-b glass-divider">
								<td class="p-3"><span class="font-medium opacity-90">#{task.id}</span></td>
								<td class="p-3">{task.fecha}</td>
								<td class="p-3">{task.nombre}</td>
								<td class="p-3">{task.localidad}</td>
								<td class="p-3">
									<div class="flex min-w-[9rem] flex-col gap-1.5">
										<span
											class={[
												'w-fit px-2 py-1 rounded-md text-xs font-medium border',
												task.estadoBadgeClass
											]}>{task.estadoNombre}</span
										>
										{#if task.estadoId === 'PROCESSING'}
											<div
												class="h-1.5 w-full overflow-hidden rounded-full bg-white/10"
												role="progressbar"
												aria-valuemin={0}
												aria-valuemax={100}
												aria-valuenow={task.progreso}
												aria-label="Avance de {task.nombre}"
											>
												<div
													class="h-full rounded-full bg-blue-400/80 transition-[width] duration-300"
													style="width: {task.progreso}%"
												></div>
											</div>
											<span class="text-[11px] text-blue-100/80">{task.progreso}%</span>
										{/if}
									</div>
								</td>
								<td class="p-3">{task.detalle}</td>
								<td class="p-3">
									<div class="flex gap-2">
										{#each task.acciones as accion (accion)}
											<button
												onclick={() => onAction(accion, task.id)}
												class={['glass-button text-sm py-1 px-3', ACTION_STYLES[accion]]}
												disabled={busyAction !== undefined}
											>
												{#if busyAction === accion}
													<Spinner size={14} />
													{BUSY_LABELS[accion] ?? 'Procesando...'}
												{:else}
													{accion.charAt(0).toUpperCase() + accion.slice(1)}
												{/if}
											</button>
										{/each}
									</div>
								</td>
							</tr>
						{/each}
					{/if}
				</tbody>
			</table>
		</div>
	</div>
</div>

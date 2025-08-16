<script module lang="ts">
	export type ActionType =
		| 'configurar'
		| 'revisar'
		| 'exportar'
		| 'cancelar'
		| 'archivar'
		| 'eliminar'
		| 'desarchivar';

	export interface TaskRow {
		id: number;
		fecha: string;
		nombre: string;
		localidad: string;
		estadoNombre: string;
		estadoBadgeClass: string;
		detalle: string;
		acciones: ActionType[];
	}
</script>

<script lang="ts">
	import Spinner from '$lib/components/Spinner.svelte';
	type ActionType = import('./TaskTable.svelte').ActionType;
	type TaskRow = import('./TaskTable.svelte').TaskRow;
	let {
		title,
		rows = [],
		loading = false,
		onAction,
		rightButtonLabel,
		onRightButtonClick,
		busy = {}
	} = $props<{
		title: string;
		rows: TaskRow[];
		loading?: boolean;
		onAction: (action: ActionType, id: number) => void;
		rightButtonLabel?: string;
		onRightButtonClick?: () => void;
		busy?: Record<number, ActionType | true>;
	}>();

	const ACTION_STYLES: Record<ActionType, string> = {
		configurar: 'bg-blue-500 hover:bg-blue-600',
		exportar: 'bg-blue-500 hover:bg-blue-600',
		revisar: 'bg-blue-500 hover:bg-blue-600',
		cancelar: 'bg-red-500 hover:bg-red-600',
		archivar: 'bg-gray-600 hover:bg-gray-700',
		eliminar: 'bg-red-700 hover:bg-red-800',
		desarchivar: 'bg-green-600 hover:bg-green-700'
	};

	let filter = $state('');
</script>

<div class="bg-[#1a202c] text-white h-full">
	<!-- Header -->
	<div class="flex justify-between items-center p-4 border-b border-gray-700">
		<div class="flex items-center gap-2">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-6 w-6 text-blue-500"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
				/>
			</svg>
			<h1 class="text-xl font-bold">{title}</h1>
		</div>
		{#if rightButtonLabel && onRightButtonClick}
			<button
				onclick={onRightButtonClick}
				class="bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded"
			>
				{rightButtonLabel}
			</button>
		{/if}
	</div>

	<!-- Filter -->
	<div class="p-4">
		<input
			type="text"
			placeholder="Filtrar por nombre o localidad..."
			bind:value={filter}
			class="w-full bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
		/>
	</div>

	<!-- Table -->
	<div class="overflow-x-auto px-4">
		<table class="w-full border-collapse">
			<thead>
				<tr class="bg-[#2d3748] text-gray-300">
					<th class="p-3 text-left font-medium">ID</th>
					<th class="p-3 text-left font-medium">Fecha</th>
					<th class="p-3 text-left font-medium">Nombre</th>
					<th class="p-3 text-left font-medium">Localidad</th>
					<th class="p-3 text-left font-medium">Estado</th>
					<th class="p-3 text-left font-medium">Detalle</th>
					<th class="p-3 text-left font-medium">Acciones</th>
				</tr>
			</thead>
			<tbody>
				{#if loading}
					<tr>
						<td colspan="7" class="p-6 text-center text-gray-300">Cargando...</td>
					</tr>
				{:else}
					{#each rows.filter((r: TaskRow) => (filter.trim() === '' ? true : r.nombre
									.toLowerCase()
									.includes(filter.toLowerCase()) || r.localidad
									.toLowerCase()
									.includes(filter.toLowerCase()))) as task}
						<tr class="border-b border-gray-700">
							<td class="p-3"><span class="font-medium">#{task.id}</span></td>
							<td class="p-3">{task.fecha}</td>
							<td class="p-3">{task.nombre}</td>
							<td class="p-3">{task.localidad}</td>
							<td class="p-3">
								<div class="flex items-center">
									<span class={`px-2 py-1 rounded text-xs font-medium ${task.estadoBadgeClass}`}
										>{task.estadoNombre}</span
									>
								</div>
							</td>
							<td class="p-3">{task.detalle}</td>
							<td class="p-3">
								<div class="flex gap-2">
									{#each task.acciones as accion}
										{@const isBusy = !!busy[task.id]}
										{@const activeAction = busy[task.id] as ActionType | true}
										<button
											onclick={() => !isBusy && onAction(accion as ActionType, task.id)}
											class={`${ACTION_STYLES[accion as ActionType] ?? 'bg-blue-500 hover:bg-blue-600'} text-white text-sm py-1 px-3 rounded disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-1`}
											disabled={isBusy}
										>
											{#if isBusy && (activeAction === true || activeAction === (accion as ActionType))}
												<Spinner size={14} />
												{accion === 'archivar'
													? 'Archivando...'
													: accion === 'eliminar'
														? 'Eliminando...'
														: accion === 'desarchivar'
															? 'Desarchivando...'
															: 'Procesando...'}
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

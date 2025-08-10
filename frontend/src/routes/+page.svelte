<!-- src/routes/+page.svelte (refactor) -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { apiFetch } from '$lib/api';
	import { showConfirm } from '$lib/dialog';

	// Backend response types
	interface TaskResponse {
		id: number;
		name: string;
		locality: { id: number; name: string; district: { id: number; name: string } };
		name_video: string;
		duration: number; // seconds
		status: { id: string; name: string };
		date: string | Date;
		created_at: string;
	}

	type ActionType = 'configurar' | 'revisar' | 'exportar' | 'cancelar' | 'archivar' | 'eliminar';

	// Centralized status metadata to keep UI logic in one place
	const STATUS_META: Record<string, { badgeClass: string; actions: ActionType[] }> = {
		VIDEO_UPLOADED: {
			badgeClass: 'bg-gray-900 text-gray-200',
			actions: ['configurar', 'eliminar']
		},
		CONFIGURED: { badgeClass: 'bg-indigo-900 text-indigo-200', actions: ['configurar'] },
		PROCESSING: { badgeClass: 'bg-blue-900 text-blue-200', actions: [] },
		REVIEW: {
			badgeClass: 'bg-yellow-900 text-yellow-200',
			actions: ['revisar', 'archivar', 'eliminar']
		},
		APPROVED: { badgeClass: 'bg-green-900 text-green-200', actions: [] },
		ARCHIVED: { badgeClass: 'bg-gray-800 text-gray-300', actions: [] }
	};

	const ACTION_STYLES: Record<ActionType, string> = {
		configurar: 'bg-blue-500 hover:bg-blue-600',
		exportar: 'bg-blue-500 hover:bg-blue-600',
		revisar: 'bg-blue-500 hover:bg-blue-600',
		cancelar: 'bg-red-500 hover:bg-red-600',
		archivar: 'bg-gray-600 hover:bg-gray-700',
		eliminar: 'bg-red-700 hover:bg-red-800'
	};

	// View-model used by the table
	interface TaskRow {
		id: number;
		fecha: string;
		nombre: string;
		localidad: string;
		estadoNombre: string;
		estadoBadgeClass: string;
		detalle: string;
		acciones: ActionType[];
	}

	let rows = $state<TaskRow[]>([]);
	let loading = $state({ active: false });
	let filter = $state('');

	function formatDate(d: string | Date): string {
		const date = typeof d === 'string' ? new Date(d) : d;
		return date.toLocaleDateString('es-AR', { year: '2-digit', month: '2-digit', day: '2-digit' });
	}

	function formatDuration(seconds: number): string {
		const m = Math.floor(seconds / 60);
		const s = Math.floor(seconds % 60);
		return `${m}m ${s}s`;
	}

	function mapToRow(task: TaskResponse): TaskRow {
		const meta = STATUS_META[task.status.id] ?? { badgeClass: '', actions: [] };
		return {
			id: task.id,
			fecha: formatDate(task.date),
			nombre: task.name,
			localidad: task.locality.name,
			estadoNombre: task.status.name,
			estadoBadgeClass: meta.badgeClass,
			detalle: formatDuration(task.duration),
			acciones: meta.actions
		};
	}

	async function fetchActiveTasks() {
		loading.active = true;
		try {
			const response = await apiFetch('/task');
			if (!response.ok)
				throw new Error(`Error fetching tasks: ${response.status} ${response.statusText}`);
			const fetched: TaskResponse[] = await response.json();
			rows = fetched.map(mapToRow);
		} catch (error) {
			console.error('Error fetching tasks:', error);
		} finally {
			loading.active = false;
		}
	}

	onMount(async () => {
		await fetchActiveTasks();
	});

	async function archiveTask(taskId: number) {
		const res = await apiFetch(`/task/${taskId}/archive`, { method: 'POST' });
		if (!res.ok) throw new Error('No se pudo archivar la tarea');
		await fetchActiveTasks();
	}

	async function deleteTask(taskId: number) {
		const confirmed = await showConfirm({
			message:
				'¿Seguro que querés eliminar esta tarea? Esta acción es permanente y no se puede deshacer.\nSe eliminarán todos los datos asociados (historiales, configuraciones) y los archivos del bucket.',
			variant: 'danger',
			confirmText: 'Eliminar',
			cancelText: 'Cancelar'
		});
		if (!confirmed) return;
		const res = await apiFetch(`/task/${taskId}`, { method: 'DELETE' });
		if (!res.ok) throw new Error('No se pudo eliminar la tarea');
		await fetchActiveTasks();
	}

	function handleAction(action: ActionType, taskId: number): void {
		switch (action) {
			case 'configurar':
				goto(`/tarea/${taskId}/configurar`);
				break;
			case 'revisar':
				goto(`/tarea/${taskId}/revisar`);
				break;
			case 'exportar':
				console.log(`Exportando tarea ${taskId}`);
				break;
			case 'cancelar':
				console.log(`Cancelando tarea ${taskId}`);
				break;
			case 'archivar':
				archiveTask(taskId).catch((e) => console.error(e));
				break;
			case 'eliminar':
				deleteTask(taskId).catch((e) => console.error(e));
				break;
		}
	}

	function goToCreateTask(): void {
		goto('/tarea/crear');
	}

	let { data } = $props();
</script>

<div class="bg-[#1a202c] text-white h-full">
	<!-- Header con título y botón crear -->
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
			<h1 class="text-xl font-bold">Tareas</h1>
		</div>
		<button
			onclick={goToCreateTask}
			class="bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded">Crear Tarea</button
		>
	</div>

	<!-- Barra de filtro -->
	<div class="p-4">
		<input
			type="text"
			placeholder="Filtrar por nombre o localidad..."
			bind:value={filter}
			class="w-full bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
		/>
	</div>

	<!-- Tabla de tareas -->
	<div class="overflow-x-auto px-4">
		<table class="w-full border-collapse">
			<!-- Encabezados de tabla -->
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
			<!-- Cuerpo de la tabla -->
			<tbody>
				{#each rows.filter((r) => (filter.trim() === '' ? true : r.nombre
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
									<button
										onclick={() => handleAction(accion, task.id)}
										class={`${ACTION_STYLES[accion]} text-white text-sm py-1 px-3 rounded`}
									>
										{accion.charAt(0).toUpperCase() + accion.slice(1)}
									</button>
								{/each}
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>

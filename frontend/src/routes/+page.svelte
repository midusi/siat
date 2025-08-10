<!-- src/routes/+page.svelte -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { apiFetch } from '$lib/api';

	interface Task {
		id: number;
		fecha: string;
		localidad: string;
		vias: string;
		estado: string;
		detalle: string;
		acciones: string[];
	}

	let tasks = $state<Task[]>([]);
	let loading = $state({ active: false });

	const taskActions: Record<string, string[]> = {
		'Video subido': ['configurar'],
		Revisión: ['revisar', 'archivar']
	};

	async function fetchActiveTasks() {
		loading.active = true;
		try {
			const response = await apiFetch('/task');
			if (!response.ok)
				throw new Error(`Error fetching tasks: ${response.status} ${response.statusText}`);
			const fetchedTasks = await response.json();
			tasks = fetchedTasks.map((task: any) => ({
				id: task.id,
				fecha: new Date(task.date).toLocaleDateString('es-AR', {
					year: '2-digit',
					month: '2-digit',
					day: '2-digit'
				}),
				localidad: task.locality.name,
				vias: task.name_video,
				estado: task.status.name,
				detalle: `${Math.floor(task.duration / 60)}m ${task.duration % 60}s`,
				acciones: taskActions[task.status.name] || []
			}));
		} catch (error) {
			console.error('Error fetching tasks:', error);
		} finally {
			loading.active = false;
		}
	}

	onMount(async () => {
		await fetchActiveTasks();
	});

	function getStatusIcon(estado: string): string {
		switch (estado) {
			case 'Subido':
			case 'Video subido':
				return '⚪';
			case 'Procesando':
				return '▶️';
			case 'Revisión':
				return '📄';
			case 'Aprobado':
				return '✓';
			default:
				return '';
		}
	}

	function getActionClass(accion: string): string {
		switch (accion) {
			case 'configurar':
				return 'bg-blue-500 hover:bg-blue-600';
			case 'exportar':
				return 'bg-blue-500 hover:bg-blue-600';
			case 'revisar':
				return 'bg-blue-500 hover:bg-blue-600';
			case 'cancelar':
				return 'bg-red-500 hover:bg-red-600';
			case 'archivar':
				return 'bg-gray-600 hover:bg-gray-700';
			default:
				return 'bg-blue-500 hover:bg-blue-600';
		}
	}

	async function archiveTask(taskId: number) {
		const res = await apiFetch(`/task/${taskId}/archive`, { method: 'POST' });
		if (!res.ok) throw new Error('No se pudo archivar la tarea');
		await fetchActiveTasks();
	}

	function handleAction(action: string, taskId: number): void {
		if (action === 'configurar') {
			goto(`/tarea/${taskId}/configurar`);
		} else if (action === 'revisar') {
			goto(`/tarea/${taskId}/revisar`);
		} else if (action === 'exportar') {
			console.log(`Exportando tarea ${taskId}`);
		} else if (action === 'cancelar') {
			console.log(`Cancelando tarea ${taskId}`);
		} else if (action === 'archivar') {
			archiveTask(taskId).catch((e) => console.error(e));
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
			class="bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded"
		>
			Crear Tarea
		</button>
	</div>

	<!-- Barra de filtro -->
	<div class="p-4">
		<input
			type="text"
			placeholder="Filtrar..."
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
					<th class="p-3 text-left font-medium">Localidad</th>
					<th class="p-3 text-left font-medium">Vias</th>
					<th class="p-3 text-left font-medium">Estado</th>
					<th class="p-3 text-left font-medium">Detalle</th>
					<th class="p-3 text-left font-medium">Acciones</th>
				</tr>
			</thead>
			<!-- Cuerpo de la tabla -->
			<tbody>
				{#each tasks as task}
					<tr class="border-b border-gray-700">
						<td class="p-3">
							<span class="font-medium">#{task.id}</span>
						</td>
						<td class="p-3">
							{task.fecha}
						</td>
						<td class="p-3">
							{task.localidad}
						</td>
						<td class="p-3">
							{task.vias}
						</td>
						<td class="p-3">
							<div class="flex items-center gap-2">
								<span class="text-lg">{getStatusIcon(task.estado)}</span>
								<span>{task.estado}</span>
							</div>
						</td>
						<td class="p-3">
							{task.detalle}
						</td>
						<td class="p-3">
							<div class="flex gap-2">
								{#each task.acciones as accion}
									<button
										onclick={() => handleAction(accion, task.id)}
										class={`${getActionClass(accion)} text-white text-sm py-1 px-3 rounded`}
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

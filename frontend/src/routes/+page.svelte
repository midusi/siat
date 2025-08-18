<!-- src/routes/+page.svelte (refactor to use TaskTable) -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { apiFetch } from '$lib/api';
	import { showConfirm } from '$lib/dialog';
	import TaskTable from '$lib/components/TaskTable.svelte';
	import type { ActionType, TaskRow } from '$lib/components/TaskTable.svelte';

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

	// Centralized status metadata to keep UI logic in one place
	const STATUS_META: Record<string, { badgeClass: string; actions: ActionType[] }> = {
		VIDEO_UPLOADED: {
			badgeClass: 'border border-white/20 bg-white/10',
			actions: ['configurar', 'eliminar']
		},
		CONFIGURED: {
			badgeClass: 'border border-indigo-300/30 bg-indigo-300/10 text-indigo-100',
			actions: ['configurar', 'eliminar']
		},
		PROCESSING: {
			badgeClass: 'border border-blue-300/30 bg-blue-300/10 text-blue-100',
			actions: ['eliminar']
		},
		PROCESSED: {
			badgeClass: 'border border-yellow-300/30 bg-yellow-300/10 text-yellow-100',
			actions: ['revisar', 'archivar', 'eliminar']
		},
		APPROVED: {
			badgeClass: 'border border-green-300/30 bg-green-300/10 text-green-100',
			actions: ['eliminar']
		},
		ARCHIVED: {
			badgeClass: 'border border-white/10 bg-white/5 text-white/70',
			actions: ['eliminar']
		}
	};

	let rows = $state<TaskRow[]>([]);
	let loading = $state({ active: false });
	let busy = $state<Record<number, import('$lib/components/TaskTable.svelte').ActionType | true>>(
		{}
	);

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
		busy[taskId] = 'archivar';
		const res = await apiFetch(`/task/${taskId}/archive`, { method: 'POST' });
		if (!res.ok) throw new Error('No se pudo archivar la tarea');
		delete busy[taskId];
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
		busy[taskId] = 'eliminar';
		const res = await apiFetch(`/task/${taskId}`, { method: 'DELETE' });
		if (!res.ok) throw new Error('No se pudo eliminar la tarea');
		delete busy[taskId];
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
			default:
				break;
		}
	}

	function goToCreateTask(): void {
		goto('/tarea/crear');
	}

	let { data } = $props();
</script>

<div class="page-container">
	<TaskTable
		title="Tareas"
		{rows}
		loading={loading.active}
		onAction={handleAction}
		{busy}
		rightButtonLabel="Crear Tarea"
		onRightButtonClick={goToCreateTask}
	/>
</div>

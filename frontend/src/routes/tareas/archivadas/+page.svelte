<script lang="ts">
	import TaskTable from '$lib/components/TaskTable.svelte';
	import type { TaskRow, ActionType } from '$lib/components/TaskTable.svelte';
	import { apiFetch } from '$lib/api';
	import { showConfirm } from '$lib/dialog';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

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

	async function fetchArchived() {
		loading.active = true;
		try {
			const res = await apiFetch('/task/archived');
			if (!res.ok) throw new Error('No se pudieron cargar las tareas archivadas');
			const data = await res.json();
			rows = data.map((task: any) => ({
				id: task.id,
				fecha: formatDate(task.date),
				nombre: task.name,
				localidad: task.locality.name,
				estadoNombre: 'Archivada',
				estadoBadgeClass: 'bg-gray-800 text-gray-300',
				detalle: formatDuration(task.duration),
				acciones: ['desarchivar', 'eliminar'] as ActionType[]
			}));
		} catch (e) {
			console.error(e);
		} finally {
			loading.active = false;
		}
	}

	onMount(fetchArchived);

	async function unarchiveTask(taskId: number) {
		busy[taskId] = 'desarchivar';
		const res = await apiFetch(`/task/${taskId}/unarchive`, { method: 'POST' });
		if (!res.ok) return console.error('No se pudo desarchivar');
		delete busy[taskId];
		await fetchArchived();
	}

	async function deleteTask(taskId: number) {
		const confirmed = await showConfirm({
			message:
				'¿Seguro que querés eliminar esta tarea? Esta acción es permanente y no se puede deshacer.\nSe eliminarán todos los datos asociados y los archivos del bucket.',
			variant: 'danger',
			confirmText: 'Eliminar',
			cancelText: 'Cancelar'
		});
		if (!confirmed) return;
		busy[taskId] = 'eliminar';
		const res = await apiFetch(`/task/${taskId}`, { method: 'DELETE' });
		if (!res.ok) return console.error('No se pudo eliminar la tarea');
		delete busy[taskId];
		await fetchArchived();
	}

	function handleAction(action: ActionType, id: number) {
		if (action === 'desarchivar') return unarchiveTask(id);
		if (action === 'eliminar') return deleteTask(id);
	}
</script>

<TaskTable
	title="Tareas archivadas"
	{rows}
	loading={loading.active}
	onAction={handleAction}
	{busy}
	rightButtonLabel="Volver"
	onRightButtonClick={() => goto('/')}
/>

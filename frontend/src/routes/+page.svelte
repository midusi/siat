<script lang="ts">
	import { actionDispatcher, createTaskList } from '$lib/task-list.svelte';
	import { archiveTask, fetchTasks } from '$lib/services/tasks';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import type { TaskEvent } from '$lib/types/task';
	import TaskTable from '$lib/components/TaskTable.svelte';

	const tasks = createTaskList(fetchTasks);

	const handleAction = actionDispatcher({
		configurar: (id) => goto(`/tarea/${id}/configurar`),
		revisar: (id) => goto(`/tarea/${id}/revisar`),
		archivar: (id) => tasks.run(id, 'archivar', () => archiveTask(id)),
		eliminar: tasks.confirmDelete
	});

	onMount(() => {
		tasks.load();
		const eventSource = new EventSource('/api/events');
		eventSource.onmessage = (event) => {
			try {
				const data: TaskEvent = JSON.parse(event.data);
				if (!data.task_id) {
					return;
				}
				const row = tasks.rows.find((item) => item.id === data.task_id);
				const statusChanged = Boolean(data.status) && row?.estadoId !== data.status;
				if (typeof data.progress === 'number' && row && !statusChanged) {
					row.progreso = data.progress;
					return;
				}
				if (data.status) {
					tasks.load();
				}
			} catch (e) {
				console.error('Error parsing SSE event:', e);
			}
		};

		return () => eventSource.close();
	});
</script>

<div class="page-container">
	<TaskTable
		title="Tareas"
		rows={tasks.rows}
		loading={tasks.loading}
		busy={tasks.busy}
		onAction={handleAction}
		rightButtonLabel="Crear Tarea"
		onRightButtonClick={() => goto('/tarea/crear')}
	/>
</div>

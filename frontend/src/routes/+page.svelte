<script lang="ts">
	import { actionDispatcher, createTaskList } from '$lib/task-list.svelte';
	import { archiveTask, fetchTasks } from '$lib/services/tasks';
	import { BACKEND_URL } from '$lib/constants';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import TaskTable from '$lib/components/TaskTable.svelte';

	import type { ActionDispatch, TaskList } from '$lib/task-list.svelte';
	import type { TaskEvent, TaskRow } from '$lib/types/task';

	const tasks: TaskList = createTaskList(fetchTasks);

	const handleAction: ActionDispatch = actionDispatcher({
		configurar: (id) => goto(`/tareas/${id}/configurar`),
		revisar: (id) => goto(`/tareas/${id}/revisar`),
		archivar: (id) => tasks.run(id, 'archivar', () => archiveTask(id)),
		eliminar: tasks.confirmDelete
	});

	onMount(() => {
		tasks.load();
		const eventSource: EventSource = new EventSource(`${BACKEND_URL}/events`);
		eventSource.onmessage = (event) => {
			try {
				const data: TaskEvent = JSON.parse(event.data);
				if (!data.task_id) {
					return;
				}
				const row: TaskRow | undefined = tasks.rows.find((item) => item.id === data.task_id);
				const statusChanged: boolean = Boolean(data.status) && row?.estadoId !== data.status;
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
		onRightButtonClick={() => goto('/tareas/crear')}
	/>
</div>

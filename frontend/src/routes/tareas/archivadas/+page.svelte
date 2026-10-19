<script lang="ts">
	import { actionDispatcher, createTaskList } from '$lib/task-list.svelte';
	import { fetchArchivedTasks, unarchiveTask } from '$lib/services/tasks';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import TaskTable from '$lib/components/TaskTable.svelte';

	const tasks = createTaskList(fetchArchivedTasks);

	const handleAction = actionDispatcher({
		desarchivar: (id) => tasks.run(id, 'desarchivar', () => unarchiveTask(id)),
		eliminar: tasks.confirmDelete
	});

	onMount(() => {
		tasks.load();
	});
</script>

<div class="page-container">
	<TaskTable
		title="Tareas archivadas"
		rows={tasks.rows}
		loading={tasks.loading}
		busy={tasks.busy}
		onAction={handleAction}
		rightButtonLabel="Volver"
		onRightButtonClick={() => goto('/')}
	/>
</div>

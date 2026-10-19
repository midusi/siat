import { type ActionType, type TaskResponse, type TaskRow, toTaskRow } from '$lib/types/task';
import { deleteTask } from '$lib/services/tasks';
import { errorMessage } from '$lib/services/errors';
import { showConfirm } from '$lib/dialog';
import { showError } from '$lib/toast';

export type ActionHandlers = Partial<Record<ActionType, (taskId: number) => void>>;

export const actionDispatcher =
	(handlers: ActionHandlers) =>
	(action: ActionType, taskId: number): void =>
		handlers[action]?.(taskId);

const DELETE_MESSAGE: string =
	'¿Seguro que querés eliminar esta tarea? Esta acción es permanente y no se puede deshacer.\nSe eliminarán todos los datos asociados (historiales, configuraciones) y los archivos del bucket.';

export const createTaskList = (fetcher: () => Promise<TaskResponse[]>) => {
	let rows = $state<TaskRow[]>([]);
	let loading = $state(false);
	const busy = $state<Record<number, ActionType | true>>({});

	const load = async () => {
		loading = true;
		try {
			rows = (await fetcher()).map(toTaskRow);
		} catch (e) {
			showError(errorMessage(e));
		} finally {
			loading = false;
		}
	};

	const run = async (taskId: number, action: ActionType, request: () => Promise<void>) => {
		busy[taskId] = action;
		try {
			await request();
			await load();
		} catch (e) {
			showError(errorMessage(e));
		} finally {
			delete busy[taskId];
		}
	};

	const confirmDelete = async (taskId: number) => {
		const confirmed = await showConfirm({
			message: DELETE_MESSAGE,
			variant: 'danger',
			confirmText: 'Eliminar',
			cancelText: 'Cancelar'
		});
		if (!confirmed) {
			return;
		}
		await run(taskId, 'eliminar', () => deleteTask(taskId));
	};

	return {
		get rows() {
			return rows;
		},
		get loading() {
			return loading;
		},
		get busy() {
			return busy;
		},
		load,
		run,
		confirmDelete
	};
};

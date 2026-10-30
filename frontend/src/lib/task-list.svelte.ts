import { deleteTask } from '$lib/services/tasks';
import { errorMessage } from '$lib/services/errors';
import { formatDate, formatDuration } from '$lib/format';
import { showConfirm } from '$lib/dialog.svelte';
import { showError } from '$lib/toast.svelte';

import type { ActionType, TaskResponse, TaskRow, TaskStatusId } from '$lib/types/task';

export type ActionDispatch = (action: ActionType, taskId: number) => void;
export type ActionHandlers = Partial<Record<ActionType, (taskId: number) => void>>;
export type TaskList = ReturnType<typeof createTaskList>;

type StatusMeta = {
	badgeClass: string;
	actions: Array<ActionType>;
};

const STATUS_META: Record<TaskStatusId, StatusMeta> = {
	VIDEO_UPLOADED: {
		badgeClass: 'border border-white/20 bg-white/10',
		actions: ['configurar', 'eliminar']
	},
	CONFIGURED: {
		badgeClass: 'border border-indigo-300/30 bg-indigo-300/10 text-indigo-100',
		actions: ['configurar', 'eliminar']
	},
	READY_TO_PROCESS: {
		badgeClass: 'border border-cyan-300/30 bg-cyan-300/10 text-cyan-100',
		actions: ['eliminar']
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
		actions: ['desarchivar', 'eliminar']
	}
};

const UNKNOWN_STATUS_META: StatusMeta = { badgeClass: '', actions: [] };

const DELETE_MESSAGE: string =
	'¿Seguro que querés eliminar esta tarea? Esta acción es permanente y no se puede deshacer.\nSe eliminarán todos los datos asociados (historiales, configuraciones) y los archivos del bucket.';

export const actionDispatcher =
	(handlers: ActionHandlers): ActionDispatch =>
	(action: ActionType, taskId: number): void =>
		handlers[action]?.(taskId);

const toTaskRow = (task: TaskResponse): TaskRow => {
	const meta: StatusMeta = STATUS_META[task.status.id] ?? UNKNOWN_STATUS_META;
	return {
		id: task.id,
		fecha: formatDate(task.date),
		nombre: task.name,
		localidad: task.locality.name,
		estadoNombre: task.status.name,
		estadoId: task.status.id,
		estadoBadgeClass: meta.badgeClass,
		detalle: formatDuration(task.duration),
		progreso: task.progress ?? 0,
		acciones: meta.actions
	};
};

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

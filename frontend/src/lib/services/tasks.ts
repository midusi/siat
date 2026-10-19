import { apiFetch } from '$lib/api';
import type { TaskResponse } from '$lib/types/task';
import { apiError } from './errors';

const TASK_API: string = '/task';

export const fetchTasks = async (): Promise<TaskResponse[]> => {
	const res = await apiFetch(TASK_API);
	if (!res.ok) {
		throw await apiError(res, 'No se pudieron cargar las tareas');
	}
	return (await res.json()) as TaskResponse[];
};

export const fetchArchivedTasks = async (): Promise<TaskResponse[]> => {
	const res = await apiFetch(`${TASK_API}/archived`);
	if (!res.ok) {
		throw await apiError(res, 'No se pudieron cargar las tareas archivadas');
	}
	return (await res.json()) as TaskResponse[];
};

export const archiveTask = async (id: number): Promise<void> => {
	const res = await apiFetch(`${TASK_API}/${id}/archive`, { method: 'POST' });
	if (!res.ok) {
		throw await apiError(res, 'No se pudo archivar la tarea');
	}
};

export const unarchiveTask = async (id: number): Promise<void> => {
	const res = await apiFetch(`${TASK_API}/${id}/unarchive`, { method: 'POST' });
	if (!res.ok) {
		throw await apiError(res, 'No se pudo desarchivar la tarea');
	}
};

export const deleteTask = async (id: number): Promise<void> => {
	const res = await apiFetch(`${TASK_API}/${id}`, { method: 'DELETE' });
	if (!res.ok) {
		throw await apiError(res, 'No se pudo eliminar la tarea');
	}
};

export interface NewTask {
	name: string;
	localityId: number;
	date: string;
	objectKey: string;
}

export const createTask = async (task: NewTask): Promise<void> => {
	const body = new FormData();
	body.append('name', task.name);
	body.append('locality_id', String(task.localityId));
	body.append('date', task.date);
	body.append('object_key', task.objectKey);
	const res = await apiFetch(TASK_API, { method: 'POST', body });
	if (!res.ok) {
		throw await apiError(res, 'No se pudo crear la tarea');
	}
};

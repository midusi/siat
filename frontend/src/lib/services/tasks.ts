import { ApiError, apiError } from './errors';
import { apiFetch } from '$lib/api';

import type { FirstFrameInfo, TaskConfigPayload, TaskResponse } from '$lib/types/task';

export type NewTask = {
	name: string;
	localityId: number;
	date: string;
	objectKey: string;
};

const TASK_API: string = '/task';

export const fetchTasks = async (): Promise<Array<TaskResponse>> => {
	const res: Response = await apiFetch(TASK_API);
	if (!res.ok) {
		throw await apiError(res, 'No se pudieron cargar las tareas');
	}
	return (await res.json()) as Array<TaskResponse>;
};

export const fetchArchivedTasks = async (): Promise<Array<TaskResponse>> => {
	const res: Response = await apiFetch(`${TASK_API}/archived`);
	if (!res.ok) {
		throw await apiError(res, 'No se pudieron cargar las tareas archivadas');
	}
	return (await res.json()) as Array<TaskResponse>;
};

export const archiveTask = async (id: number): Promise<void> => {
	const res: Response = await apiFetch(`${TASK_API}/${id}/archive`, { method: 'POST' });
	if (!res.ok) {
		throw await apiError(res, 'No se pudo archivar la tarea');
	}
};

export const unarchiveTask = async (id: number): Promise<void> => {
	const res: Response = await apiFetch(`${TASK_API}/${id}/unarchive`, { method: 'POST' });
	if (!res.ok) {
		throw await apiError(res, 'No se pudo desarchivar la tarea');
	}
};

export const deleteTask = async (id: number): Promise<void> => {
	const res: Response = await apiFetch(`${TASK_API}/${id}`, { method: 'DELETE' });
	if (!res.ok) {
		throw await apiError(res, 'No se pudo eliminar la tarea');
	}
};

export const createTask = async (task: NewTask): Promise<void> => {
	const body: FormData = new FormData();
	body.append('name', task.name);
	body.append('locality_id', String(task.localityId));
	body.append('date', task.date);
	body.append('object_key', task.objectKey);
	const res: Response = await apiFetch(TASK_API, { method: 'POST', body });
	if (!res.ok) {
		throw await apiError(res, 'No se pudo crear la tarea');
	}
};

export const fetchFirstFrame = async (id: number): Promise<FirstFrameInfo> => {
	const res: Response = await apiFetch(`${TASK_API}/${id}/get-first-frame-info`);
	if (!res.ok) {
		throw await apiError(res, 'No se pudo cargar la imagen');
	}
	const info: FirstFrameInfo = (await res.json()) as FirstFrameInfo;
	if (!info.image_b64) {
		throw new ApiError('La respuesta no contiene la imagen');
	}
	return info;
};

export const saveTaskConfig = async (id: number, payload: TaskConfigPayload): Promise<void> => {
	const res: Response = await apiFetch(`${TASK_API}/${id}/config`, {
		method: 'POST',
		body: JSON.stringify(payload)
	});
	if (!res.ok) {
		throw await apiError(res, 'No se pudieron guardar las vías');
	}
};

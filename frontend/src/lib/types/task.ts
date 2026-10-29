import { z } from 'zod';

export type ActionType =
	| 'configurar'
	| 'revisar'
	| 'exportar'
	| 'cancelar'
	| 'archivar'
	| 'eliminar'
	| 'desarchivar';

export interface TaskRow {
	id: number;
	fecha: string;
	nombre: string;
	localidad: string;
	estadoNombre: string;
	estadoId: TaskStatusId;
	estadoBadgeClass: string;
	detalle: string;
	progreso: number;
	acciones: Array<ActionType>;
}

export interface TaskResponse {
	id: number;
	name: string;
	locality: { id: number; name: string; district: { id: number; name: string } };
	name_video: string;
	duration: number;
	status: { id: TaskStatusId; name: string };
	date: string | Date;
	created_at: string;
	progress?: number;
}

export type TaskStatusId =
	| 'VIDEO_UPLOADED'
	| 'CONFIGURED'
	| 'READY_TO_PROCESS'
	| 'PROCESSING'
	| 'PROCESSED'
	| 'APPROVED'
	| 'ARCHIVED';

export interface TaskEvent {
	task_id: number;
	status?: TaskStatusId;
	progress?: number;
}

export interface FirstFrameInfo {
	width: number;
	height: number;
	image_b64: string;
}

export type AbsolutePoint = [number, number];

export interface Road {
	name: string;
	polygon: Array<AbsolutePoint>;
}

export interface TaskConfigPayload {
	roads_in: Array<Road>;
	roads_out: Array<Road>;
	excluded_zones: Array<Array<AbsolutePoint>>;
}

export interface StatusMeta {
	badgeClass: string;
	actions: Array<ActionType>;
}

export const STATUS_META = {
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
} satisfies Record<TaskStatusId, StatusMeta>;

export function formatTaskDate(d: string | Date): string {
	const date = typeof d === 'string' ? new Date(d) : d;
	return date.toLocaleDateString('es-AR', { year: '2-digit', month: '2-digit', day: '2-digit' });
}

export const localDateString = (d: Date = new Date()): string =>
	`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

export function formatDuration(seconds: number): string {
	const m = Math.floor(seconds / 60);
	const s = Math.floor(seconds % 60);
	return `${m}m ${s}s`;
}

export function toTaskRow(task: TaskResponse): TaskRow {
	const meta: StatusMeta = STATUS_META[task.status.id] ?? { badgeClass: '', actions: [] };
	return {
		id: task.id,
		fecha: formatTaskDate(task.date),
		nombre: task.name,
		localidad: task.locality.name,
		estadoNombre: task.status.name,
		estadoId: task.status.id,
		estadoBadgeClass: meta.badgeClass,
		detalle: formatDuration(task.duration),
		progreso: task.progress ?? 0,
		acciones: meta.actions
	};
}

export const ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov'];
export const INVALID_VIDEO_MESSAGE = 'El archivo debe ser .mp4, .avi o .mov';

export const isAllowedVideo = (file: File): boolean => {
	const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
	return ALLOWED_VIDEO_EXTENSIONS.includes(ext);
};

export const TaskFormSchema = z.object({
	name: z.string().min(1, 'El nombre es obligatorio'),
	date: z
		.string()
		.min(1, 'La fecha es obligatoria')
		.refine((val) => val <= localDateString(), { message: 'La fecha no puede ser mayor a hoy' }),
	selectedProvince: z
		.number()
		.nullable()
		.refine((val) => val !== null, { message: 'Seleccione una provincia' }),
	selectedDistrict: z
		.number()
		.nullable()
		.refine((val) => val !== null, { message: 'Seleccione un distrito' }),
	selectedLocality: z
		.number()
		.nullable()
		.refine((val) => val !== null, { message: 'Seleccione una localidad' }),
	file: z
		.instanceof(File, { message: 'Debe seleccionar un archivo' })
		.or(z.null())
		.refine((file) => !!file, { message: 'Debe seleccionar un archivo' })
		.refine((file) => !!file && isAllowedVideo(file), { message: INVALID_VIDEO_MESSAGE })
});

export type TaskForm = {
	name: string;
	date: string;
	selectedProvince: number | null;
	selectedDistrict: number | null;
	selectedLocality: number | null;
	file: File | null;
};

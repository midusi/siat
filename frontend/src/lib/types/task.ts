export type ActionType =
	| 'configurar'
	| 'revisar'
	| 'exportar'
	| 'cancelar'
	| 'archivar'
	| 'eliminar'
	| 'desarchivar';

export type TaskStatusId =
	| 'VIDEO_UPLOADED'
	| 'CONFIGURED'
	| 'READY_TO_PROCESS'
	| 'PROCESSING'
	| 'PROCESSED'
	| 'APPROVED'
	| 'ARCHIVED';

type District = {
	id: number;
	name: string;
};

type Locality = {
	id: number;
	name: string;
	district: District;
};

type TaskStatus = {
	id: TaskStatusId;
	name: string;
};

export type TaskResponse = {
	id: number;
	name: string;
	locality: Locality;
	name_video: string;
	duration: number;
	status: TaskStatus;
	date: string | Date;
	created_at: string;
	progress?: number;
};

export type TaskRow = {
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
};

export type TaskEvent = {
	task_id: number;
	status?: TaskStatusId;
	progress?: number;
};

export type FirstFrameInfo = {
	width: number;
	height: number;
	image_b64: string;
};

export type AbsolutePoint = [number, number];

export type Road = {
	name: string;
	polygon: Array<AbsolutePoint>;
};

export type TaskConfigPayload = {
	roads_in: Array<Road>;
	roads_out: Array<Road>;
	excluded_zones: Array<Array<AbsolutePoint>>;
};

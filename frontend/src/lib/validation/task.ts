import { localDateString } from '$lib/format';
import { z } from 'zod';

export type TaskForm = z.infer<typeof TaskFormSchema>;

export const ALLOWED_VIDEO_EXTENSIONS: Array<string> = ['.mp4', '.avi', '.mov'];
export const INVALID_VIDEO_MESSAGE: string = 'El archivo debe ser .mp4, .avi o .mov';
const FILE_REQUIRED_MESSAGE: string = 'Debe seleccionar un archivo';

export const isAllowedVideo = (file: File): boolean => {
	const extension: string = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
	return ALLOWED_VIDEO_EXTENSIONS.includes(extension);
};

export const TaskFormSchema = z.object({
	name: z.string().min(1, 'El nombre es obligatorio'),
	date: z
		.string()
		.min(1, 'La fecha es obligatoria')
		.refine((value: string): boolean => value <= localDateString(), {
			message: 'La fecha no puede ser mayor a hoy'
		}),
	selectedProvince: z
		.number()
		.nullable()
		.refine((value: number | null): boolean => value !== null, {
			message: 'Seleccione una provincia'
		}),
	selectedDistrict: z
		.number()
		.nullable()
		.refine((value: number | null): boolean => value !== null, {
			message: 'Seleccione un distrito'
		}),
	selectedLocality: z
		.number()
		.nullable()
		.refine((value: number | null): boolean => value !== null, {
			message: 'Seleccione una localidad'
		}),
	file: z
		.instanceof(File, { message: FILE_REQUIRED_MESSAGE })
		.or(z.null())
		.refine((file: File | null): boolean => file !== null, { message: FILE_REQUIRED_MESSAGE })
		.refine((file: File | null): boolean => file !== null && isAllowedVideo(file), {
			message: INVALID_VIDEO_MESSAGE
		})
});

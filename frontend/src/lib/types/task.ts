import { z } from 'zod';

export interface Task {
  id: number;
  fecha: string;
  localidad: string;
  vias: string;
  estado: 'Subido' | 'Procesando' | 'Revisión' | 'Aprobado';
  detalle: string;
  acciones: Array<'asignar' | 'archivar' | 'cancelar' | 'exportar' | 'revisar'>;
}

const allowedExtensions = ['.mp4', '.avi', '.mov'];

export const TaskFormSchema = z.object({
  name: z.string().min(1, 'El nombre es obligatorio'),
  date: z.string()
    .min(1, 'La fecha es obligatoria')
    .refine(
      (val) => {
        const today = new Date();
        const inputDate = new Date(val);
        today.setHours(0,0,0,0);
        inputDate.setHours(0,0,0,0);
        return inputDate < today;
      },
      { message: 'La fecha no puede ser mayor a hoy' }
    ),
  selectedProvince: z.number().nullable().refine(val => val !== null, { message: 'Seleccione una provincia' }),
  selectedDistrict: z.number().nullable().refine(val => val !== null, { message: 'Seleccione un distrito' }),
  selectedLocality: z.number().nullable().refine(val => val !== null, { message: 'Seleccione una localidad' }),
  file: z
    .instanceof(File, { message: 'Debe seleccionar un archivo' })
    .or(z.null())
    .refine((file) => !!file, { message: 'Debe seleccionar un archivo' })
    .refine(
      (file) => {
        if (!file) return false;
        const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
        return allowedExtensions.includes(ext);
      },
      { message: 'El archivo debe ser .mp4, .avi o .mov' }
    )
});

export type TaskForm = {
  name: string;
  date: string;
  selectedProvince: number | null;
  selectedDistrict: number | null;
  selectedLocality: number | null;
  file: File | null;
}; 
// Definición de tipos para las tareas
export interface Task {
    id: number;
    fecha: string;
    localidad: string;
    vias: string;
    estado: 'Subido' | 'Procesando' | 'Revisión' | 'Aprobado';
    detalle: string;
    acciones: Array<'asignar' | 'archivar' | 'cancelar' | 'exportar' | 'revisar'>;
}

// Definición de tipos para los elementos del menú
export interface MenuItem {
    id: string;
    label: string;
    path: string;
    icon: string;
}
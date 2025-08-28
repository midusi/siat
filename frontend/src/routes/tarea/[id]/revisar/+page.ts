// frontend/src/routes/tarea/[id]/revisar/+page.ts
import type { PageLoad } from './$types';

/**
 * La función `load` se ejecuta en el servidor (o en el cliente para navegaciones).
 * Su propósito es obtener los datos necesarios para renderizar la página.
 * Aquí, extraemos el 'id' de la tarea desde los parámetros de la URL.
 */
export const load: PageLoad = ({ params }) => {
	// El valor de 'params.id' corresponde a la parte [id] de la ruta.
	// Retornamos un objeto que estará disponible en el componente +page.svelte
	// a través de la prop `data`.
	return {
		id: params.id
	};
};

<!-- src/routes/+page.svelte -->
<script lang="ts">
	import { goto } from '$app/navigation';
	
	// Datos de ejemplo para la tabla
	const tasks = [
	  {
		id: 5,
		fecha: '24/8/30',
		localidad: 'La Plata, Bs As',
		vias: '-',
		estado: 'Subido',
		detalle: '2m 30s',
		acciones: ['configurar', 'archivar'] // Cambiado de 'asignar' a 'configurar'
	  },
	  {
		id: 4,
		fecha: '24/8/30',
		localidad: 'Echeverry, Bs As',
		vias: 'Ruta 2, Ruta 215',
		estado: 'Procesando',
		detalle: '5m 12s - 20m 30s...',
		acciones: ['cancelar', 'archivar']
	  },
	  {
		id: 3,
		fecha: '24/8/15',
		localidad: 'Venado Tuerto, Santa Fé',
		vias: 'Ruta 8, Ruta 33',
		estado: 'Revisión',
		detalle: '4m 15s - 1588 eventos',
		acciones: ['exportar', 'revisar']
	  },
	  {
		id: 2,
		fecha: '23/7/12',
		localidad: 'Brandsen, Bs As',
		vias: 'Ruta 215, Ruta 29',
		estado: 'Aprobado',
		detalle: '20m 54s - 1234 eventos',
		acciones: ['exportar', 'revisar']
	  }
	];
  
	// Función para obtener el ícono según el estado
	function getStatusIcon(estado: string): string {
	  switch (estado) {
		case 'Subido': return '⚪'; // Círculo
		case 'Procesando': return '▶️'; // Triángulo play
		case 'Revisión': return '📄'; // Documento
		case 'Aprobado': return '✓'; // Check
		default: return '';
	  }
	}
  
	// Función para obtener la clase de color según la acción
	function getActionClass(accion: string): string {
	  switch (accion) {
		case 'configurar': return 'bg-blue-500 hover:bg-blue-600'; // Misma clase que tenía 'asignar'
		case 'exportar': return 'bg-blue-500 hover:bg-blue-600';
		case 'revisar': return 'bg-blue-500 hover:bg-blue-600';
		case 'cancelar': return 'bg-red-500 hover:bg-red-600';
		case 'archivar': return 'bg-gray-600 hover:bg-gray-700';
		default: return 'bg-blue-500 hover:bg-blue-600';
	  }
	}
	
	// Función para manejar las acciones de los botones
	function handleAction(action: string, taskId: number): void {
	  if (action === 'configurar') {
		goto(`/tarea/${taskId}/configurar`);
	  } else if (action === 'revisar') {
		goto(`/tarea/${taskId}/revisar`);
	  } else if (action === 'exportar') {
		console.log(`Exportando tarea ${taskId}`);
	  } else if (action === 'cancelar') {
		console.log(`Cancelando tarea ${taskId}`);
	  } else if (action === 'archivar') {
		console.log(`Archivando tarea ${taskId}`);
	  }
	}
	
	// Función para navegar a la página de crear tarea
	function goToCreateTask(): void {
	  goto('/tarea/crear');
	}
  </script>
  
  <div class="bg-[#1a202c] text-white h-full">
	<!-- Header con título y botón crear -->
	<div class="flex justify-between items-center p-4 border-b border-gray-700">
	  <div class="flex items-center gap-2">
		<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
		  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
		</svg>
		<h1 class="text-xl font-bold">Tareas</h1>
	  </div>
	  <button 
		onclick={goToCreateTask}
		class="bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded"
	  >
		Crear Tarea
	  </button>
	</div>
  
	<!-- Barra de filtro -->
	<div class="p-4">
	  <input 
		type="text" 
		placeholder="Filtrar..." 
		class="w-full bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
	  />
	</div>
  
	<!-- Tabla de tareas -->
	<div class="overflow-x-auto px-4">
	  <table class="w-full border-collapse">
		<!-- Encabezados de tabla -->
		<thead>
		  <tr class="bg-[#2d3748] text-gray-300">
			<th class="p-3 text-left font-medium">ID</th>
			<th class="p-3 text-left font-medium">Fecha</th>
			<th class="p-3 text-left font-medium">Localidad</th>
			<th class="p-3 text-left font-medium">Vias</th>
			<th class="p-3 text-left font-medium">Estado</th>
			<th class="p-3 text-left font-medium">Detalle</th>
			<th class="p-3 text-left font-medium">Acciones</th>
		  </tr>
		</thead>
		<!-- Cuerpo de la tabla -->
		<tbody>
		  {#each tasks as task}
			<tr class="border-b border-gray-700">
			  <td class="p-3">
				<span class="font-medium">#{task.id}</span>
			  </td>
			  <td class="p-3">
				{task.fecha}
			  </td>
			  <td class="p-3">
				{task.localidad}
			  </td>
			  <td class="p-3">
				{task.vias}
			  </td>
			  <td class="p-3">
				<div class="flex items-center gap-2">
				  <span class="text-lg">{getStatusIcon(task.estado)}</span>
				  <span>{task.estado}</span>
				</div>
			  </td>
			  <td class="p-3">
				{task.detalle}
			  </td>
			  <td class="p-3">
				<div class="flex gap-2">
				  {#each task.acciones as accion}
					<button 
					  onclick={() => handleAction(accion, task.id)}
					  class={`${getActionClass(accion)} text-white text-sm py-1 px-3 rounded`}
					>
					  {accion.charAt(0).toUpperCase() + accion.slice(1)}
					</button>
				  {/each}
				</div>
			  </td>
			</tr>
		  {/each}
		</tbody>
	  </table>
	</div>
  </div>
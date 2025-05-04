<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  
  // Obtener el ID de la tarea de los parámetros de la URL
  const taskId = $page.params.id;
  
  // Estado para las vías
  let vias = $state([
    { id: 1, via: 'Ruta 2', sentido: 'Entrada' },
    { id: 2, via: 'Ruta 2', sentido: 'Salida' }
  ]);
  
  // Estado para el formulario de nueva vía
  let selectedVia = $state('Ruta 33');
  let selectedSentido = $state('Entrada');
  
  // Estado para el modal
  let showModal = $state(false);
  let modalVia = $state('Ruta 33');
  let modalSentido = $state('Entrada');
  
  // Opciones para los selects
  const opcionesVias = ['Ruta 2', 'Ruta 8', 'Ruta 33', 'Ruta 215'];
  const opcionesSentido = ['Entrada', 'Salida'];
  
  // Función para añadir una nueva vía
  function addVia(): void {
    const newId = vias.length > 0 ? Math.max(...vias.map(v => v.id)) + 1 : 1;
    vias = [...vias, { id: newId, via: selectedVia, sentido: selectedSentido }];
  }
  
  // Función para guardar los cambios
  function saveChanges(): void {
    console.log('Guardando vías:', vias);
    // Aquí iría la lógica para guardar en el backend
    alert('Vías guardadas correctamente');
  }
  
  // Función para volver a la página anterior
  function goBack(): void {
    // Volver a la página de detalle de la tarea
    goto(`/`);
  }
  
  // Función para abrir el modal de dibujo
  function handleDraw(): void {
    showModal = true;
  }
  
  // Función para cerrar el modal
  function closeModal(): void {
    showModal = false;
  }
  
  // Función para confirmar el dibujo
  function confirmDraw(): void {
    console.log('Dibujando con:', { via: modalVia, sentido: modalSentido });
    
    // Aquí iría la lógica para dibujar con los datos seleccionados
    
    // Cerrar el modal después de confirmar
    closeModal();
    
    // Opcional: añadir la vía a la lista si no existe
    const viaExists = vias.some(v => v.via === modalVia && v.sentido === modalSentido);
    if (!viaExists) {
      const newId = vias.length > 0 ? Math.max(...vias.map(v => v.id)) + 1 : 1;
      vias = [...vias, { id: newId, via: modalVia, sentido: modalSentido }];
    }
  }
</script>

<div class="min-h-screen bg-[#1a1e2a] text-white">
  <!-- Header -->
  <header class="bg-[#1a1e2a] p-4 border-b border-gray-800 flex items-center">
    <button 
      onclick={goBack}
      class="text-white mr-4"
      aria-label="Volver"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
      </svg>
    </button>
    <div class="flex items-center">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-blue-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
      <h1 class="text-xl font-semibold truncate">Asignar Vías - Tarea #{taskId}</h1>
    </div>
  </header>
  
  <!-- Contenido principal - Responsive con flex-col en móvil y flex-row en desktop -->
  <div class="flex flex-col lg:flex-row h-[calc(100vh-64px)] overflow-auto">
    <!-- Área de visualización de imagen/video -->
    <div class="w-full lg:flex-1 p-4 flex flex-col">
      <!-- Contenedor de la imagen con tamaño responsive -->
      <div class="mx-auto w-full lg:w-[80%] max-w-4xl">
        <div class="bg-black rounded-md overflow-hidden">
          <!-- Imagen de muestra (frame del video) -->
          <img
            src="/images/rotonda_manual.png"
            alt="Primer frame del video"
            class="w-full h-auto"
          />
        </div>
        
        <!-- Controles de la imagen -->
        <div class="flex justify-center gap-4 mt-4 mb-4 lg:mb-0">
          <button
            onclick={handleDraw}
            class="bg-white hover:bg-gray-300 text-gray-700 py-2 px-4 rounded"
          >
            Dibujar
          </button>
        </div>
      </div>
    </div>
    
    <!-- Panel de vías - Ancho completo en móvil, fijo en desktop -->
    <div class="w-full lg:w-96 bg-[#151923] p-4 border-t lg:border-t-0 lg:border-l border-gray-800">
      <h2 class="text-xl font-semibold mb-4">Vías</h2>
      
      <!-- Tabla de vías existentes - Responsive con scroll horizontal -->
      <div class="bg-[#1a1e2a] rounded-md overflow-x-auto mb-6">
        <table class="w-full min-w-[400px]">
          <thead>
            <tr class="bg-[#2d3748] text-gray-300">
              <th class="p-3 text-left font-medium">ID</th>
              <th class="p-3 text-left font-medium">Vía</th>
              <th class="p-3 text-left font-medium">Sentido</th>
            </tr>
          </thead>
          <tbody>
            {#each vias as via}
              <tr class="border-b border-gray-700">
                <td class="p-3">#{via.id}</td>
                <td class="p-3">{via.via}</td>
                <td class="p-3">
                  <div class="flex items-center">
                    <span 
                      class={`w-3 h-3 rounded-full mr-2 ${
                        via.sentido === 'Entrada' ? 'bg-green-500' : 'bg-red-500'
                      }`}
                    ></span>
                    {via.sentido}
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      
      <!-- Botones de acción -->
      <div class="flex gap-4 pt-4">
        <button 
          onclick={saveChanges}
          class="flex-1 bg-blue-600 hover:bg-blue-500 text-white py-3 rounded-md font-medium transition-colors"
        >
          Guardar
        </button>
      </div>
    </div>
  </div>
  
  <!-- Modal para dibujar -->
  {#if showModal}
    <div class="fixed inset-0 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div class="bg-[#1a202c] rounded-lg shadow-lg p-6 w-full max-w-md">
        <h3 class="text-xl font-semibold mb-4">Dibujar Vía</h3>
        
        <div class="space-y-4">
          <div>
            <label for="modal-via" class="block text-sm font-medium text-gray-400 mb-1">Vía</label>
            <select 
              id="modal-via" 
              bind:value={modalVia}
              class="w-full bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {#each opcionesVias as opcion}
                <option value={opcion}>{opcion}</option>
              {/each}
            </select>
          </div>
          
          <div>
            <label for="modal-sentido" class="block text-sm font-medium text-gray-400 mb-1">Sentido</label>
            <select 
              id="modal-sentido" 
              bind:value={modalSentido}
              class="w-full bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {#each opcionesSentido as opcion}
                <option value={opcion}>{opcion}</option>
              {/each}
            </select>
          </div>
        </div>
        
        <div class="flex justify-end gap-3 mt-6">
          <button 
            onclick={closeModal}
            class="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded"
          >
            Cancelar
          </button>
          <button 
            onclick={confirmDraw}
            class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded"
          >
            Confirmar
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>
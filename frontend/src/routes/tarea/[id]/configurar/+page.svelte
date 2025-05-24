<script lang="ts">
  import { tick } from 'svelte';
  import { goto } from '$app/navigation';

  let canvas: HTMLCanvasElement | null = null;
  let ctx: CanvasRenderingContext2D | null = null;
  let drawing = false;
  let showModal = false;

  let modalVia = 'Ruta 2';
  let modalSentido = 'Entrada';
  let opcionesVias = ['Ruta 2', 'Ruta 8', 'Ruta 33', 'Ruta 215'];
  let opcionesSentido = ['Entrada', 'Salida'];
  let startX = 0;
  let startY = 0;
  let isDragging = false;

  let puntos: Array<{ x: number, y: number }> = [];

  let poligonos: Array<{
    via: string;
    sentido: string;
    vertices: Array<{ x: number, y: number }>;
  }> = [];

  function handleDraw() {
     puntos.length =0;
    showModal = true;
  }

 async function confirmarYVolver() {
  console.log('Guardando polígonos:', poligonos);

  try {
    const response = await fetch('http://127.0.0.1:8000/guardar_poligonos', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(poligonos)
    });

    if (!response.ok) {
      throw new Error(`Error en la petición: ${response.statusText}`);
    }

    const data = await response.json();
    console.log('Respuesta del backend:', data);

    // Volver a la página anterior
    history.back();

  } catch (error) {
    console.error('Error enviando los polígonos:', error);
  }
}


  function handleMouseDown(event: MouseEvent) {
  if (!canvas) return;

  const rect = canvas.getBoundingClientRect();
  startX = event.clientX - rect.left;
  startY = event.clientY - rect.top;
  isDragging = true;
}

function handleMouseMove(event: MouseEvent) {
  if (!canvas || !ctx || !isDragging) return;

  const rect = canvas.getBoundingClientRect();
  const currentX = event.clientX - rect.left;
  const currentY = event.clientY - rect.top;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  redrawConfirmedPolygons();

  ctx.strokeStyle = modalSentido === 'Entrada' ? 'green' : 'red';
  ctx.lineWidth = 2;
  ctx.strokeRect(startX, startY, currentX - startX, currentY - startY);
}

function handleMouseUp(event: MouseEvent) {
  if (!canvas || !ctx || !isDragging) return;

  const rect = canvas.getBoundingClientRect();
  const endX = event.clientX - rect.left;
  const endY = event.clientY - rect.top;

  isDragging = false;

  const x1 = startX;
  const y1 = startY;
  const x2 = endX;
  const y2 = endY;

  // Generar los 4 vértices del rectángulo
  puntos = [
    { x: x1, y: y1 },
    { x: x2, y: y1 },
    { x: x2, y: y2 },
    { x: x1, y: y2 }
  ];

  poligonos = [...poligonos, {
    via: modalVia,
    sentido: modalSentido,
    vertices: [...puntos]
  }];

  puntos = [];
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  redrawConfirmedPolygons();
}

  function closeModal() {
    showModal = false;
  }

 function confirmDraw() {
  showModal = false;
  drawing = true;
  puntos = [];

  tick().then(() => {
    if (canvas) {
      ctx = canvas.getContext('2d');
      redrawConfirmedPolygons();

      canvas.addEventListener('mousedown', handleMouseDown);
      canvas.addEventListener('mousemove', handleMouseMove);
      canvas.addEventListener('mouseup', handleMouseUp);
    }
  });
}

  function handleCanvasClick(event: MouseEvent) {
    if (!canvas || !ctx) return;

    if (puntos.length >= 4) {
      alert('Ya se marcaron los 4 vértices. Confirmá o inicia otro dibujo.');
      puntos.length =0;
      return;
    }

    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    puntos.push({ x, y });
    console.log(`Vértice ${puntos.length}: ${Math.round(x)}, ${Math.round(y)}`);

    ctx.fillStyle = modalSentido === 'Entrada' ? 'green' : 'red';
    ctx.fillRect(x - 5, y - 5, 10, 10);

    if (puntos.length === 4) {
      // Guardamos el polígono
      poligonos = [...poligonos,
          {
            via: modalVia,
            sentido: modalSentido,
            vertices: [...puntos]
          }
        ];

      console.log('Todos los polígonos:', poligonos);
          

      // Limpiamos el canvas y redibujamos todos los confirmados
      puntos = [];
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      redrawConfirmedPolygons();
    }
  }

  function redrawConfirmedPolygons() {
  if (!ctx || !canvas) return;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  for (const poly of poligonos) {
    // Dibujar contorno
    ctx.beginPath();
    ctx.moveTo(poly.vertices[0].x, poly.vertices[0].y);
    for (let i = 1; i < poly.vertices.length; i++) {
      ctx.lineTo(poly.vertices[i].x, poly.vertices[i].y);
    }
    ctx.closePath();
    ctx.strokeStyle = poly.sentido === 'Entrada' ? 'green' : 'red';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Dibujar vértices
    for (const v of poly.vertices) {
      ctx.fillStyle = poly.sentido === 'Entrada' ? 'green' : 'red';
      ctx.fillRect(v.x - 5, v.y - 5, 10, 10);
    }

    // Calcular centroide del polígono
    const centro = poly.vertices.reduce(
      (acc, v) => ({ x: acc.x + v.x, y: acc.y + v.y }),
      { x: 0, y: 0 }
    );
    centro.x /= poly.vertices.length;
    centro.y /= poly.vertices.length;

    // Dibujar el texto centrado
    ctx.font = '12px sans-serif';
    ctx.fillStyle = 'white';
    ctx.textAlign = 'center';
    ctx.fillText(`${poly.via} - ${poly.sentido}`, centro.x, centro.y - 10);

    console.log('Polígonos confirmados:', poligonos);
  }
}

 function eliminarPoligono(index: number) {
  poligonos = poligonos.filter((_, i) => i !== index);
  redrawConfirmedPolygons();
}


</script>

<style>
  canvas {
    position: absolute;
    top: 0;
    left: 0;
    pointer-events: auto;
    cursor: crosshair;
  }
</style>

<!-- Fondo oscuro -->
<div class="min-h-screen bg-[#1a1e2a] text-white py-8 px-4">
  <div class="max-w-5xl mx-auto">
    <h1 class="text-2xl font-bold mb-6">Asignar vías - Dibujar sobre imagen</h1>

    <!-- Imagen con canvas superpuesto -->
    <div class="relative w-full rounded overflow-hidden bg-black">
      <img src="/images/rotonda_manual.png" alt="Imagen base" class="w-full h-auto opacity-90" />

      {#if drawing}
        <canvas
          bind:this={canvas}
          width={canvas?.parentElement?.clientWidth}
          height={canvas?.parentElement?.clientHeight}
          class="absolute top-0 left-0 z-10"
        ></canvas>
      {/if}
    </div>
    

    <!-- Botón para abrir modal -->
    <div class="flex justify-center mt-6 gap-4">
      <button
        on:click={handleDraw}
        class="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-md"
      >
        Dibujar
      </button>

      <button
    on:click={confirmarYVolver}
    class="bg-green-600 hover:bg-green-500 text-white px-6 py-2 rounded-md"
  >
    Confirmar cambios y volver
  </button>


    </div>
  </div>
  
  



  <!-- Lista de polígonos confirmados -->
  <div class="max-w-5xl mx-auto mt-10">
    <h2 class="text-xl font-semibold mb-4">Polígonos confirmados</h2>

    {#if poligonos.length === 0}
      <p class="text-gray-400">Todavía no se han dibujado polígonos.</p>
    {:else}
      <div class="space-y-4">
        {#each poligonos as poly, index}
          <div class="bg-[#2d3748] p-4 rounded border border-gray-700">
            <div class="flex justify-between items-center mb-2">
              <div>
                <p><strong>#{index + 1}</strong> - 
                  <span class="text-blue-400">{poly.via}</span> - 
                  <span class={poly.sentido === 'Entrada' ? 'text-green-400' : 'text-red-400'}>
                    {poly.sentido}
                  </span>
                </p>
              </div>
              <div class="flex gap-2">
                <button on:click={() => eliminarPoligono(index)} class="text-red-400 hover:underline text-sm">Eliminar</button>
              </div>
            </div>
            <ul class="text-sm pl-4 list-disc">
              {#each poly.vertices as v, vi}
                <li>Vértice {vi + 1}: ({Math.round(v.x)}, {Math.round(v.y)})</li>
              {/each}
            </ul>
          </div>
        {/each}
      </div>
    {/if}
  </div>

  <!-- Modal -->
  {#if showModal}
    <div class="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
      <div class="bg-[#1a202c] text-white p-6 rounded-lg space-y-4 w-full max-w-sm shadow-lg">
        <h2 class="text-lg font-semibold">Dibujar vía</h2>

        <div>
          <label class="block mb-1 text-sm">Vía:</label>
          <select bind:value={modalVia} class="w-full bg-[#2d3748] text-white p-2 rounded border border-gray-600">
            {#each opcionesVias as opcion}
              <option value={opcion}>{opcion}</option>
            {/each}
          </select>
        </div>

        <div>
          <label class="block mb-1 text-sm">Sentido:</label>
          <select bind:value={modalSentido} class="w-full bg-[#2d3748] text-white p-2 rounded border border-gray-600">
            {#each opcionesSentido as opcion}
              <option value={opcion}>{opcion}</option>
            {/each}
          </select>
        </div>

        <div class="flex justify-end gap-3 pt-4">
          <button on:click={closeModal} class="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded">
            Cancelar
          </button>
          <button on:click={confirmDraw} class="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded">
            Confirmar
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>

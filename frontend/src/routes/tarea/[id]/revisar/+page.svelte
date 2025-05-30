
<script lang="ts">
  // Datos simulados (puedes reemplazarlos luego con un fetch al backend)
  let videoPath = "/video/videoPrueba.mp4"; // Make sure this path is correct if you are serving it

  // Updated estadisticas object based on your image
  let estadisticas = {
    entradas: {
      titulo: "Entradas",
      columnasPrincipales: ["A", "B", "C", "D"],
      datos: [
        { tipo: "Auto", a: "1,59%", b: "23,91%", c: "13,13%", d: "0,00%", tasaError: "9,66%", manual: 243, modelo: 266 },
        { tipo: "Moto", a: "54,55%", b: "33,33%", c: "11,76%", d: "22,22%", tasaError: "30,47%", manual: 40, modelo: 37 },
        { tipo: "Camión Liviano", a: "0,00%", b: "50,00%", c: "37,50%", d: "0,00%", tasaError: "21,88%", manual: 11, modelo: 15 },
        { tipo: "Camión Pesado", a: "0,00%", b: "200,00%", c: "50,00%", d: "0,00%", tasaError: "62,50%", manual: 7, modelo: 10 },
        { tipo: "Colectivo", a: "0,00%", b: "0,00%", c: "0,00%", d: "0,00%", tasaError: "0,00%", manual: 1, modelo: 1 },
        { tipo: "Bici", a: "100,00%", b: "100,00%", c: "0,00%", d: "100,00%", tasaError: "75,00%", manual: 6, modelo: 2 },
      ],
      total: { a: "26,02%", b: "67,87%", c: "18,73%", d: "20,37%", tasaError: "33,25%", manual: 308, modelo: 331 }
    },
    salidas: {
      titulo: "Salidas",
      columnasPrincipales: ["A", "B", "C", "D"],
      datos: [
        { tipo: "Auto", a: "24,71%", b: "12,00%", c: "11,54%", d: "12,50%", tasaError: "15,19%", manual: 252, modelo: 293 },
        { tipo: "Moto", a: "73,33%", b: "0,00%", c: "35,71%", d: "50,00%", tasaError: "39,76%", manual: 40, modelo: 36 },
        { tipo: "Camión Liviano", a: "0,00%", b: "0,00%", c: "100,00%", d: "0,00%", tasaError: "25,00%", manual: 11, modelo: 15 },
        { tipo: "Camión Pesado", a: "150,00%", b: "0,00%", c: "50,00%", d: "0,00%", tasaError: "50,00%", manual: 8, modelo: 8 },
        { tipo: "Colectivo", a: "0,00%", b: "0,00%", c: "0,00%", d: "0,00%", tasaError: "0,00%", manual: 1, modelo: 1 },
        { tipo: "Bici", a: "100,00%", b: "0,00%", c: "100,00%", d: "0,00%", tasaError: "50,00%", manual: 5, modelo: 0 },
      ],
      total: { a: "58,01%", b: "2,00%", c: "49,54%", d: "10,42%", tasaError: "29,99%", manual: 317, modelo: 353 }
    },
    rutas: {
      titulo: "Rutas",
      columnasSalida: ["Salida A", "Salida B", "Salida C", "Salida D"],
      entradasDetalle: [
        {
          nombreEntrada: "Entrada A",
          datos: [
            { tipo: "Auto", salidaA: "100,00%", salidaB: "0,00%", salidaC: "8,89%", salidaD: "100,00%", tasaError: "47,33%", manual: 241, modelo: 288 },
            { tipo: "Moto", salidaA: "0,00%", salidaB: "0,00%", salidaC: "100,00%", salidaD: "0,00%", tasaError: "43,75%", manual: 36, modelo: 37 },
            { tipo: "Camión Liviano", salidaA: "0,00%", salidaB: "0,00%", salidaC: "0,00%", salidaD: "0,00%", tasaError: "22,92%", manual: 11, modelo: 15 },
            { tipo: "Camión Pesado", salidaA: "0,00%", salidaB: "0,00%", salidaC: "0,00%", salidaD: "0,00%", tasaError: "12,50%", manual: 7, modelo: 10 },
            { tipo: "Colectivo", salidaA: "0,00%", salidaB: "0,00%", salidaC: "0,00%", salidaD: "0,00%", tasaError: "6,25%", manual: 1, modelo: 1 },
            { tipo: "Bicicleta", salidaA: "0,00%", salidaB: "0,00%", salidaC: "100,00%", salidaD: "0,00%", tasaError: "18,75%", manual: 5, modelo: 2 },
          ],
          total: { salidaA: "16,67%", salidaB: "0,00%", salidaC: "34,81%", salidaD: "16,67%", tasaError: "25,25%", manual: 0, modelo: 0 } // Manual/Modelo Totals for Rutas were not specified for total row, put 0 or sum if available
        },
        {
          nombreEntrada: "Entrada B",
          datos: [
            { tipo: "Auto", salidaA: "100,00%", salidaB: "0,00%", salidaC: "0,00%", salidaD: "100,00%", tasaError: "47,33%", manual: 241, modelo: 288 }, // Data from image for Entrada B seems to be a copy of A, adjust if different
            { tipo: "Moto", salidaA: "0,00%", salidaB: "0,00%", salidaC: "0,00%", salidaD: "0,00%", tasaError: "43,75%", manual: 36, modelo: 37 },
            { tipo: "Camión Liviano", salidaA: "0,00%", salidaB: "0,00%", salidaC: "0,00%", salidaD: "100,00%", tasaError: "22,92%", manual: 11, modelo: 15 },
            { tipo: "Camión Pesado", salidaA: "0,00%", salidaB: "0,00%", salidaC: "100,00%", salidaD: "0,00%", tasaError: "12,50%", manual: 7, modelo: 10 },
            { tipo: "Colectivo", salidaA: "0,00%", salidaB: "0,00%", salidaC: "0,00%", salidaD: "0,00%", tasaError: "6,25%", manual: 1, modelo: 1 },
            { tipo: "Bicicleta", salidaA: "0,00%", salidaB: "0,00%", salidaC: "0,00%", salidaD: "0,00%", tasaError: "18,75%", manual: 5, modelo: 2 },
          ],
          total: { salidaA: "16,67%", salidaB: "0,00%", salidaC: "16,67%", salidaD: "50,00%", tasaError: "25,25%", manual: 0, modelo: 0 }
        },
        {
          nombreEntrada: "Entrada C",
          datos: [
            { tipo: "Auto", salidaA: "85,94%", salidaB: "91,67%", salidaC: "75,00%", salidaD: "73,68%", tasaError: "47,33%", manual: 241, modelo: 288 },
            { tipo: "Moto", salidaA: "100,00%", salidaB: "100,00%", salidaC: "0,00%", salidaD: "100,00%", tasaError: "43,75%", manual: 36, modelo: 37 },
            { tipo: "Camión Liviano", salidaA: "66,67%", salidaB: "100,00%", salidaC: "100,00%", salidaD: "0,00%", tasaError: "22,92%", manual: 11, modelo: 15 },
            { tipo: "Camión Pesado", salidaA: "100,00%", salidaB: "0,00%", salidaC: "0,00%", salidaD: "0,00%", tasaError: "12,50%", manual: 7, modelo: 10 },
            { tipo: "Colectivo", salidaA: "100,00%", salidaB: "0,00%", salidaC: "0,00%", salidaD: "0,00%", tasaError: "6,25%", manual: 1, modelo: 1 },
            { tipo: "Bicicleta", salidaA: "100,00%", salidaB: "0,00%", salidaC: "0,00%", salidaD: "0,00%", tasaError: "18,75%", manual: 5, modelo: 2 },
          ],
          total: { salidaA: "92,10%", salidaB: "48,61%", salidaC: "29,17%", salidaD: "28,95%", tasaError: "25,25%", manual: 0, modelo: 0 }
        },
        {
          nombreEntrada: "Entrada D",
          datos: [
            { tipo: "Auto", salidaA: "0,00%", salidaB: "15,38%", salidaC: "6,67%", salidaD: "0,00%", tasaError: "47,33%", manual: 241, modelo: 288 },
            { tipo: "Moto", salidaA: "100,00%", salidaB: "0,00%", salidaC: "100,00%", salidaD: "0,00%", tasaError: "43,75%", manual: 36, modelo: 37 },
            { tipo: "Camión Liviano", salidaA: "0,00%", salidaB: "0,00%", salidaC: "0,00%", salidaD: "0,00%", tasaError: "22,92%", manual: 11, modelo: 15 },
            { tipo: "Camión Pesado", salidaA: "0,00%", salidaB: "0,00%", salidaC: "0,00%", salidaD: "0,00%", tasaError: "12,50%", manual: 7, modelo: 10 },
            { tipo: "Colectivo", salidaA: "0,00%", salidaB: "0,00%", salidaC: "0,00%", salidaD: "0,00%", tasaError: "6,25%", manual: 1, modelo: 1 },
            { tipo: "Bicicleta", salidaA: "100,00%", salidaB: "0,00%", salidaC: "0,00%", salidaD: "0,00%", tasaError: "18,75%", manual: 5, modelo: 2 },
          ],
          total: { salidaA: "33,33%", salidaB: "2,56%", salidaC: "17,78%", salidaD: "0,00%", tasaError: "25,25%", manual: 0, modelo: 0 }
        },
      ]
    }
  };

  // Helper function to get keys for dynamic access in Entradas/Salidas
  function getColumnKeys(item: any, cols: string[]) {
    return cols.map(col => item[col.toLowerCase() as keyof typeof item]);
  }
</script>

<div class="min-h-screen bg-[#1a1e2a] text-white py-8 px-4">
  <div class="max-w-7xl mx-auto"> <!-- Increased max-width for wider tables -->
    <h1 class="text-3xl font-bold mb-8 text-center">Revisar Video Analizado</h1>

    <!-- Video -->
    <div class="rounded overflow-hidden border border-gray-600 bg-black mb-12">
      <video class="w-full" controls>
        <source src={videoPath} type="video/mp4" />
        Tu navegador no soporta la reproducción de video.
      </video>
    </div>

    <!-- Estadísticas Section -->
    <div class="space-y-12">

      <!-- Entradas y Salidas Tables (Side by Side on larger screens) -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
        <!-- Entradas Table -->
        <div class="bg-[#2a2f3a] p-6 rounded-lg shadow-lg">
          <h2 class="text-2xl font-semibold mb-4 text-center">{estadisticas.entradas.titulo}</h2>
          <div class="overflow-x-auto">
            <table class="w-full text-sm text-left">
              <thead class="text-xs text-gray-300 uppercase bg-[#383f4f]">
                <tr>
                  <th scope="col" class="px-4 py-3">Vehículo</th>
                  {#each estadisticas.entradas.columnasPrincipales as col}
                    <th scope="col" class="px-4 py-3 text-center">{col}</th>
                  {/each}
                  <th scope="col" class="px-4 py-3 text-center">Tasa de error</th>
                  <th scope="col" colspan="2" class="px-4 py-3 text-center">Muestra</th>
                </tr>
                <tr>
                    <th class="px-4 py-2"></th>
                    {#each estadisticas.entradas.columnasPrincipales as col} <th class="px-4 py-2"></th> {/each}
                    <th class="px-4 py-2"></th>
                    <th class="px-4 py-2 text-center text-xs">Manual</th>
                    <th class="px-4 py-2 text-center text-xs">Modelo</th>
                </tr>
              </thead>
              <tbody>
                {#each estadisticas.entradas.datos as item}
                  <tr class="border-b border-gray-700 hover:bg-[#383f4f]">
                    <td class="px-4 py-2 font-medium whitespace-nowrap">{item.tipo}</td>
                    {#each getColumnKeys(item, estadisticas.entradas.columnasPrincipales) as val}
                      <td class="px-4 py-2 text-center">{val}</td>
                    {/each}
                    <td class="px-4 py-2 text-center">{item.tasaError}</td>
                    <td class="px-4 py-2 text-center">{item.manual}</td>
                    <td class="px-4 py-2 text-center">{item.modelo}</td>
                  </tr>
                {/each}
                <tr class="font-semibold bg-[#383f4f]">
                  <td class="px-4 py-2">Total</td>
                  {#each getColumnKeys(estadisticas.entradas.total, estadisticas.entradas.columnasPrincipales) as val}
                    <td class="px-4 py-2 text-center">{val}</td>
                  {/each}
                  <td class="px-4 py-2 text-center">{estadisticas.entradas.total.tasaError}</td>
                  <td class="px-4 py-2 text-center">{estadisticas.entradas.total.manual}</td>
                  <td class="px-4 py-2 text-center">{estadisticas.entradas.total.modelo}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Salidas Table -->
        <div class="bg-[#2a2f3a] p-6 rounded-lg shadow-lg">
          <h2 class="text-2xl font-semibold mb-4 text-center">{estadisticas.salidas.titulo}</h2>
          <div class="overflow-x-auto">
            <table class="w-full text-sm text-left">
              <thead class="text-xs text-gray-300 uppercase bg-[#383f4f]">
                <tr>
                  <th scope="col" class="px-4 py-3">Vehículo</th>
                  {#each estadisticas.salidas.columnasPrincipales as col}
                    <th scope="col" class="px-4 py-3 text-center">{col}</th>
                  {/each}
                  <th scope="col" class="px-4 py-3 text-center">Tasa de error</th>
                  <th scope="col" colspan="2" class="px-4 py-3 text-center">Muestra</th>
                </tr>
                 <tr>
                    <th class="px-4 py-2"></th>
                    {#each estadisticas.salidas.columnasPrincipales as col} <th class="px-4 py-2"></th> {/each}
                    <th class="px-4 py-2"></th>
                    <th class="px-4 py-2 text-center text-xs">Manual</th>
                    <th class="px-4 py-2 text-center text-xs">Modelo</th>
                </tr>
              </thead>
              <tbody>
                {#each estadisticas.salidas.datos as item}
                  <tr class="border-b border-gray-700 hover:bg-[#383f4f]">
                    <td class="px-4 py-2 font-medium whitespace-nowrap">{item.tipo}</td>
                     {#each getColumnKeys(item, estadisticas.salidas.columnasPrincipales) as val}
                      <td class="px-4 py-2 text-center">{val}</td>
                    {/each}
                    <td class="px-4 py-2 text-center">{item.tasaError}</td>
                    <td class="px-4 py-2 text-center">{item.manual}</td>
                    <td class="px-4 py-2 text-center">{item.modelo}</td>
                  </tr>
                {/each}
                <tr class="font-semibold bg-[#383f4f]">
                  <td class="px-4 py-2">Total</td>
                   {#each getColumnKeys(estadisticas.salidas.total, estadisticas.salidas.columnasPrincipales) as val}
                    <td class="px-4 py-2 text-center">{val}</td>
                  {/each}
                  <td class="px-4 py-2 text-center">{estadisticas.salidas.total.tasaError}</td>
                  <td class="px-4 py-2 text-center">{estadisticas.salidas.total.manual}</td>
                  <td class="px-4 py-2 text-center">{estadisticas.salidas.total.modelo}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Rutas Table -->
      <div class="bg-[#2a2f3a] p-6 rounded-lg shadow-lg">
        <h2 class="text-2xl font-semibold mb-6 text-center">{estadisticas.rutas.titulo}</h2>
        <div class="space-y-8">
          {#each estadisticas.rutas.entradasDetalle as entrada}
            <div>
              <h3 class="text-xl font-medium mb-3 text-gray-300">{entrada.nombreEntrada}</h3>
              <div class="overflow-x-auto">
                <table class="w-full text-sm text-left">
                  <thead class="text-xs text-gray-300 uppercase bg-[#383f4f]">
                    <tr>
                      <th scope="col" class="px-4 py-3">Vehículo</th>
                      {#each estadisticas.rutas.columnasSalida as col}
                        <th scope="col" class="px-4 py-3 text-center">{col}</th>
                      {/each}
                      <th scope="col" class="px-4 py-3 text-center">Tasa de error</th>
                      <th scope="col" colspan="2" class="px-4 py-3 text-center">Muestra</th>
                    </tr>
                    <tr>
                        <th class="px-4 py-2"></th>
                        {#each estadisticas.rutas.columnasSalida as col} <th class="px-4 py-2"></th> {/each}
                        <th class="px-4 py-2"></th>
                        <th class="px-4 py-2 text-center text-xs">Manual</th>
                        <th class="px-4 py-2 text-center text-xs">Modelo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each entrada.datos as item}
                      <tr class="border-b border-gray-700 hover:bg-[#383f4f]">
                        <td class="px-4 py-2 font-medium whitespace-nowrap">{item.tipo}</td>
                        <td class="px-4 py-2 text-center">{item.salidaA}</td>
                        <td class="px-4 py-2 text-center">{item.salidaB}</td>
                        <td class="px-4 py-2 text-center">{item.salidaC}</td>
                        <td class="px-4 py-2 text-center">{item.salidaD}</td>
                        <td class="px-4 py-2 text-center">{item.tasaError}</td>
                        <td class="px-4 py-2 text-center">{item.manual}</td>
                        <td class="px-4 py-2 text-center">{item.modelo}</td>
                      </tr>
                    {/each}
                    <tr class="font-semibold bg-[#383f4f]">
                      <td class="px-4 py-2">Total</td>
                      <td class="px-4 py-2 text-center">{entrada.total.salidaA}</td>
                      <td class="px-4 py-2 text-center">{entrada.total.salidaB}</td>
                      <td class="px-4 py-2 text-center">{entrada.total.salidaC}</td>
                      <td class="px-4 py-2 text-center">{entrada.total.salidaD}</td>
                      <td class="px-4 py-2 text-center">{entrada.total.tasaError}</td>
                      <td class="px-4 py-2 text-center">{entrada.total.manual}</td>
                      <td class="px-4 py-2 text-center">{entrada.total.modelo}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          {/each}
        </div>
      </div>
    </div>
  </div>
</div>


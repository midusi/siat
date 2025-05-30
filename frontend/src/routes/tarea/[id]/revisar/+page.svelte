<script lang="ts">
  // Datos simulados (reemplaza con fetch si es necesario)
  let videoPath = "/video/videoPrueba.mp4"; // Asegúrate que esta ruta sea correcta

  // NUEVOS DATOS JSON
  const inOutRawData = {
    "out": [
        {
            "0": { "bicycle": 0, "bus": 0, "car": 96, "heavy_truck": 0, "light_truck": 2, "motorbike": 3, "indeterminado": 15 },
            "1": { "bicycle": 0, "bus": 0, "car": 43, "heavy_truck": 0, "light_truck": 1, "motorbike": 5, "indeterminado": 3 },
            "2": { "bicycle": 0, "bus": 1, "car": 86, "heavy_truck": 0, "light_truck": 1, "motorbike": 8, "indeterminado": 1 },
            "3": { "bicycle": 0, "bus": 0, "car": 57, "heavy_truck": 0, "light_truck": 2, "motorbike": 6, "indeterminado": 1 }
        }
    ],
    "in": [
        {
            "0": { "bicycle": 0, "bus": 0, "car": 67, "heavy_truck": 0, "light_truck": 0, "motorbike": 1, "indeterminado": 5 },
            "1": { "bicycle": 0, "bus": 0, "car": 51, "heavy_truck": 0, "light_truck": 2, "motorbike": 6, "indeterminado": 1 },
            "2": { "bicycle": 0, "bus": 0, "car": 134, "heavy_truck": 1, "light_truck": 11, "motorbike": 5, "indeterminado": 11 },
            "3": { "bicycle": 0, "bus": 0, "car": 56, "heavy_truck": 0, "light_truck": 4, "motorbike": 4, "indeterminado": 6 }
        }
    ]
  };

  const rutasRawData = {
    "0": { // Entrada A
        "0": { "bicycle": 0, "bus": 0, "car": 0, "heavy_truck": 0, "light_truck": 0, "motorbike": 0, "indeterminado": 0 }, // Salida A
        "1": { "bicycle": 0, "bus": 0, "car": 6, "heavy_truck": 0, "light_truck": 0, "motorbike": 0, "indeterminado": 0 }, // Salida B
        "2": { "bicycle": 0, "bus": 0, "car": 34, "heavy_truck": 0, "light_truck": 0, "motorbike": 0, "indeterminado": 0 },// Salida C
        "3": { "bicycle": 0, "bus": 0, "car": 8, "heavy_truck": 0, "light_truck": 0, "motorbike": 0, "indeterminado": 1 }, // Salida D
        "4": { "bicycle": 0, "bus": 0, "car": 19, "heavy_truck": 0, "light_truck": 0, "motorbike": 1, "indeterminado": 4 } // Total/Indeterminado Salida (o Salida E si existe)
    },
    "1": { // Entrada B
        "0": { "bicycle": 0, "bus": 0, "car": 2, "heavy_truck": 0, "light_truck": 0, "motorbike": 0, "indeterminado": 0 },
        "1": { "bicycle": 0, "bus": 0, "car": 1, "heavy_truck": 0, "light_truck": 0, "motorbike": 0, "indeterminado": 0 },
        "2": { "bicycle": 0, "bus": 0, "car": 19, "heavy_truck": 0, "light_truck": 0, "motorbike": 0, "indeterminado": 0 },
        "3": { "bicycle": 0, "bus": 0, "car": 23, "heavy_truck": 0, "light_truck": 1, "motorbike": 1, "indeterminado": 0 },
        "4": { "bicycle": 0, "bus": 0, "car": 6, "heavy_truck": 0, "light_truck": 1, "motorbike": 5, "indeterminado": 1 }
    },
    "2": { // Entrada C
        "0": { "bicycle": 0, "bus": 0, "car": 77, "heavy_truck": 0, "light_truck": 0, "motorbike": 0, "indeterminado": 8 },
        "1": { "bicycle": 0, "bus": 0, "car": 11, "heavy_truck": 0, "light_truck": 0, "motorbike": 0, "indeterminado": 2 },
        "2": { "bicycle": 0, "bus": 0, "car": 4, "heavy_truck": 0, "light_truck": 0, "motorbike": 0, "indeterminado": 0 },
        "3": { "bicycle": 0, "bus": 0, "car": 17, "heavy_truck": 0, "light_truck": 0, "motorbike": 2, "indeterminado": 0 },
        "4": { "bicycle": 0, "bus": 0, "car": 25, "heavy_truck": 1, "light_truck": 11, "motorbike": 3, "indeterminado": 1 }
    },
    "3": { // Entrada D
        "0": { "bicycle": 0, "bus": 0, "car": 8, "heavy_truck": 0, "light_truck": 0, "motorbike": 0, "indeterminado": 1 },
        "1": { "bicycle": 0, "bus": 0, "car": 22, "heavy_truck": 0, "light_truck": 0, "motorbike": 0, "indeterminado": 0 },
        "2": { "bicycle": 0, "bus": 0, "car": 17, "heavy_truck": 0, "light_truck": 0, "motorbike": 0, "indeterminado": 0 },
        "3": { "bicycle": 0, "bus": 0, "car": 0, "heavy_truck": 0, "light_truck": 0, "motorbike": 0, "indeterminado": 0 },
        "4": { "bicycle": 0, "bus": 0, "car": 9, "heavy_truck": 0, "light_truck": 4, "motorbike": 4, "indeterminado": 5 }
    },
    "4": { // Total Entradas / Entradas Indeterminadas (o Entrada E si existe)
        "0": { "bicycle": 0, "bus": 0, "car": 9, "heavy_truck": 0, "light_truck": 2, "motorbike": 3, "indeterminado": 6 },
        "1": { "bicycle": 0, "bus": 0, "car": 3, "heavy_truck": 0, "light_truck": 1, "motorbike": 5, "indeterminado": 1 },
        "2": { "bicycle": 0, "bus": 1, "car": 12, "heavy_truck": 0, "light_truck": 1, "motorbike": 8, "indeterminado": 1 },
        "3": { "bicycle": 0, "bus": 0, "car": 9, "heavy_truck": 0, "light_truck": 1, "motorbike": 3, "indeterminado": 0 },
        "4": { "bicycle": 2, "bus": 3, "car": 191, "heavy_truck": 1, "light_truck": 25, "motorbike": 67, "indeterminado": 39 } // Grand total o Total Indeterminados cruzados
    }
  };

  // --- Helper Functions ---
  const vehicleKeyToName = {
    bicycle: "Bicicleta",
    bus: "Colectivo",
    car: "Auto",
    heavy_truck: "Camión Pesado",
    light_truck: "Camión Liviano",
    motorbike: "Moto",
    indeterminado: "Indeterminado",
  };

  const gateKeyToLabel = (key: string, prefix = "") => {
    const numericKey = parseInt(key, 10);
    if (numericKey >= 0 && numericKey <= 3) { // Assuming 0-A, 1-B, 2-C, 3-D
      return `${prefix}${String.fromCharCode(65 + numericKey)}`;
    }
    if (numericKey === 4 && prefix.toLowerCase().includes("salida")) return `${prefix}Total`; // Special case for "Salida Total" if key is "4"
    if (numericKey === 4 && prefix.toLowerCase().includes("entrada")) return `${prefix}Total`; // Special case for "Entrada Total" if key is "4"
    return `${prefix}Key ${key}`; // Fallback
  };

  const getAllVehicleTypes = (dataObject: any): string[] => {
    const types = new Set<string>();
    for (const gateKey in dataObject) {
      for (const vehicleKey in dataObject[gateKey]) {
        types.add(vehicleKey);
      }
    }
    return Array.from(types).sort(); // Sort for consistent order
  };


  // --- Data Transformation ---
  function transformInOutData(rawData: typeof inOutRawData, type: 'in' | 'out') {
    const dataSection = rawData[type][0]; // The first (and only) element of the array
    if (!dataSection) return { titulo: type === 'in' ? "Entradas" : "Salidas", columnasPrincipales: [], datos: [], total: {} };

    const gateKeys = Object.keys(dataSection); // "0", "1", "2", "3"
    const columnasPrincipales = gateKeys.map(k => gateKeyToLabel(k)); // "A", "B", "C", "D"
    const vehicleTypes = getAllVehicleTypes(dataSection);

    const datos = vehicleTypes.map(vKey => {
      const row: { [key: string]: string | number } = { tipo: vehicleKeyToName[vKey] || vKey };
      let rowSum = 0;
      gateKeys.forEach(gKey => {
        const count = dataSection[gKey][vKey] || 0;
        row[gateKeyToLabel(gKey)] = count;
        rowSum += count;
      });
      // row.totalVehiculo = rowSum; // If you want a row total
      return row;
    });

    const total: { [key: string]: string | number } = { tipo: "Total" };
    let grandTotal = 0;
    gateKeys.forEach(gKey => {
      let colSum = 0;
      vehicleTypes.forEach(vKey => {
        colSum += (dataSection[gKey][vKey] || 0);
      });
      total[gateKeyToLabel(gKey)] = colSum;
      grandTotal += colSum;
    });
    // total.totalVehiculo = grandTotal; // Grand total for the "Total" row

    return {
      titulo: type === 'in' ? "Entradas" : "Salidas",
      columnasPrincipales,
      datos,
      total
    };
  }

  function transformRutasData(rawData: typeof rutasRawData) {
    const inputGateKeys = Object.keys(rawData); // "0", "1", "2", "3", "4" (for inputs)

    const entradasDetalle = inputGateKeys.map(inKey => {
      const currentInputData = rawData[inKey];
      const outputGateKeys = Object.keys(currentInputData); // "0", "1", "2", "3", "4" (for outputs)
      
      // Handle naming for the "4" key for inputs (Entrada Total or similar)
      let nombreEntradaDisplay = gateKeyToLabel(inKey, "Entrada ");
      if (inKey === "4") nombreEntradaDisplay = "Resumen Total Rutas";


      const columnasSalida = outputGateKeys.map(outKey => gateKeyToLabel(outKey, "Salida "));
      const vehicleTypes = getAllVehicleTypes(currentInputData);

      const datos = vehicleTypes.map(vKey => {
        const row: { [key: string]: string | number } = { tipo: vehicleKeyToName[vKey] || vKey };
        outputGateKeys.forEach(outKey => {
          row[gateKeyToLabel(outKey, "Salida ")] = currentInputData[outKey][vKey] || 0;
        });
        return row;
      });

      const total: { [key: string]: string | number } = { tipo: "Total" };
      outputGateKeys.forEach(outKey => {
        let colSum = 0;
        vehicleTypes.forEach(vKey => {
          colSum += (currentInputData[outKey][vKey] || 0);
        });
        total[gateKeyToLabel(outKey, "Salida ")] = colSum;
      });

      return {
        nombreEntrada: nombreEntradaDisplay,
        columnasSalida,
        datos,
        total
      };
    });
    
    // Define a general set of columns for the overall "Rutas" section,
    // typically based on the first entry or a union of all.
    // For simplicity, let's use the columns from the first detailed entry if available.
    // Each table will still use its own specific `entrada.columnasSalida` for rendering.
    const firstEntryColumns = entradasDetalle.length > 0 ? entradasDetalle[0].columnasSalida : [];

    return {
      titulo: "Rutas",
      columnasSalidaGlobal: firstEntryColumns, // Used for a consistent header structure IF all tables have same cols
      entradasDetalle
    };
  }

  // Processed data for the tables
  let entradasData = transformInOutData(inOutRawData, 'in');
  let salidasData = transformInOutData(inOutRawData, 'out');
  let rutasData = transformRutasData(rutasRawData);

</script>

<div class="min-h-screen bg-[#1a1e2a] text-white py-8 px-4">
  <div class="max-w-7xl mx-auto">
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

      <!-- Entradas y Salidas Tables -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
        <!-- Entradas Table -->
        {#if entradasData}
        <div class="bg-[#2a2f3a] p-6 rounded-lg shadow-lg">
          <h2 class="text-2xl font-semibold mb-4 text-center">{entradasData.titulo}</h2>
          <div class="overflow-x-auto">
            <table class="w-full text-sm text-left">
              <thead class="text-xs text-gray-300 uppercase bg-[#383f4f]">
                <tr>
                  <th scope="col" class="px-4 py-3">Vehículo</th>
                  {#each entradasData.columnasPrincipales as col}
                    <th scope="col" class="px-4 py-3 text-center">{col}</th>
                  {/each}
                  <!-- <th scope="col" class="px-4 py-3 text-center">Total Vehículo</th> -->
                </tr>
              </thead>
              <tbody>
                {#each entradasData.datos as item}
                  <tr class="border-b border-gray-700 hover:bg-[#383f4f]">
                    <td class="px-4 py-2 font-medium whitespace-nowrap">{item.tipo}</td>
                    {#each entradasData.columnasPrincipales as col}
                      <td class="px-4 py-2 text-center">{item[col]}</td>
                    {/each}
                    <!-- <td class="px-4 py-2 text-center">{item.totalVehiculo}</td> -->
                  </tr>
                {/each}
                <tr class="font-semibold bg-[#383f4f]">
                  <td class="px-4 py-2">{entradasData.total.tipo}</td>
                  {#each entradasData.columnasPrincipales as col}
                    <td class="px-4 py-2 text-center">{entradasData.total[col]}</td>
                  {/each}
                  <!-- <td class="px-4 py-2 text-center">{entradasData.total.totalVehiculo}</td> -->
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        {/if}

        <!-- Salidas Table -->
        {#if salidasData}
        <div class="bg-[#2a2f3a] p-6 rounded-lg shadow-lg">
          <h2 class="text-2xl font-semibold mb-4 text-center">{salidasData.titulo}</h2>
          <div class="overflow-x-auto">
            <table class="w-full text-sm text-left">
              <thead class="text-xs text-gray-300 uppercase bg-[#383f4f]">
                <tr>
                  <th scope="col" class="px-4 py-3">Vehículo</th>
                  {#each salidasData.columnasPrincipales as col}
                    <th scope="col" class="px-4 py-3 text-center">{col}</th>
                  {/each}
                  <!-- <th scope="col" class="px-4 py-3 text-center">Total Vehículo</th> -->
                </tr>
              </thead>
              <tbody>
                {#each salidasData.datos as item}
                  <tr class="border-b border-gray-700 hover:bg-[#383f4f]">
                    <td class="px-4 py-2 font-medium whitespace-nowrap">{item.tipo}</td>
                    {#each salidasData.columnasPrincipales as col}
                      <td class="px-4 py-2 text-center">{item[col]}</td>
                    {/each}
                     <!-- <td class="px-4 py-2 text-center">{item.totalVehiculo}</td> -->
                  </tr>
                {/each}
                <tr class="font-semibold bg-[#383f4f]">
                  <td class="px-4 py-2">{salidasData.total.tipo}</td>
                  {#each salidasData.columnasPrincipales as col}
                    <td class="px-4 py-2 text-center">{salidasData.total[col]}</td>
                  {/each}
                  <!-- <td class="px-4 py-2 text-center">{salidasData.total.totalVehiculo}</td> -->
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        {/if}
      </div>

      <!-- Rutas Table -->
      {#if rutasData}
      <div class="bg-[#2a2f3a] p-6 rounded-lg shadow-lg">
        <h2 class="text-2xl font-semibold mb-6 text-center">{rutasData.titulo}</h2>
        <div class="space-y-8">
          {#each rutasData.entradasDetalle as entrada}
            <div>
              <h3 class="text-xl font-medium mb-3 text-gray-300">{entrada.nombreEntrada}</h3>
              <div class="overflow-x-auto">
                <table class="w-full text-sm text-left">
                  <thead class="text-xs text-gray-300 uppercase bg-[#383f4f]">
                    <tr>
                      <th scope="col" class="px-4 py-3">Vehículo</th>
                      {#each entrada.columnasSalida as colName}
                        <th scope="col" class="px-4 py-3 text-center">{colName}</th>
                      {/each}
                    </tr>
                  </thead>
                  <tbody>
                    {#each entrada.datos as item}
                      <tr class="border-b border-gray-700 hover:bg-[#383f4f]">
                        <td class="px-4 py-2 font-medium whitespace-nowrap">{item.tipo}</td>
                        {#each entrada.columnasSalida as colName}
                          <td class="px-4 py-2 text-center">{item[colName]}</td>
                        {/each}
                      </tr>
                    {/each}
                    <tr class="font-semibold bg-[#383f4f]">
                      <td class="px-4 py-2">{entrada.total.tipo}</td>
                      {#each entrada.columnasSalida as colName}
                        <td class="px-4 py-2 text-center">{entrada.total[colName]}</td>
                      {/each}
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          {/each}
        </div>
      </div>
      {/if}
    </div>
  </div>
</div>
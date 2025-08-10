<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { apiFetch } from '$lib/api';

	interface Task {
		id: number;
		fecha: string;
		localidad: string;
		vias: string;
		estado: string;
		detalle: string;
		acciones: string[];
	}

	let tasks = $state<Task[]>([]);
	let loading = $state(false);

	async function fetchArchived() {
		loading = true;
		try {
			const res = await apiFetch('/task/archived');
			if (!res.ok) throw new Error('No se pudieron cargar las tareas archivadas');
			const data = await res.json();
			tasks = data.map((task: any) => ({
				id: task.id,
				fecha: new Date(task.date).toLocaleDateString('es-AR', {
					year: '2-digit',
					month: '2-digit',
					day: '2-digit'
				}),
				localidad: task.locality.name,
				vias: task.name_video,
				estado: 'Archivada',
				detalle: `${Math.floor(task.duration / 60)}m ${task.duration % 60}s`,
				acciones: ['desarchivar']
			}));
		} catch (e) {
			console.error(e);
		} finally {
			loading = false;
		}
	}

	onMount(fetchArchived);

	function getStatusIcon(estado: string): string {
		switch (estado) {
			case 'Archivada':
				return '🗄️';
			default:
				return '';
		}
	}

	function getActionClass(accion: string): string {
		return accion === 'desarchivar'
			? 'bg-green-600 hover:bg-green-700'
			: 'bg-blue-500 hover:bg-blue-600';
	}

	async function unarchiveTask(taskId: number) {
		const res = await apiFetch(`/task/${taskId}/unarchive`, { method: 'POST' });
		if (!res.ok) return console.error('No se pudo desarchivar');
		await fetchArchived();
	}
</script>

<div class="bg-[#1a202c] text-white h-full">
	<div class="flex justify-between items-center p-4 border-b border-gray-700">
		<div class="flex items-center gap-2">
			<span class="text-lg">🗄️</span>
			<h1 class="text-xl font-bold">Tareas archivadas</h1>
		</div>
		<button
			onclick={() => goto('/')}
			class="bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded">Volver</button
		>
	</div>

	<div class="overflow-x-auto px-4 mt-4">
		<table class="w-full border-collapse">
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
			<tbody>
				{#each tasks as task}
					<tr class="border-b border-gray-700">
						<td class="p-3"><span class="font-medium">#{task.id}</span></td>
						<td class="p-3">{task.fecha}</td>
						<td class="p-3">{task.localidad}</td>
						<td class="p-3">{task.vias}</td>
						<td class="p-3">
							<div class="flex items-center gap-2">
								<span class="text-lg">{getStatusIcon(task.estado)}</span>
								<span>{task.estado}</span>
							</div>
						</td>
						<td class="p-3">{task.detalle}</td>
						<td class="p-3">
							<button
								onclick={() => unarchiveTask(task.id)}
								class={`${getActionClass('desarchivar')} text-white text-sm py-1 px-3 rounded`}
								>Desarchivar</button
							>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>

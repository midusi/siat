<script lang="ts">
    import { onMount } from 'svelte';
    
    // Tipos para los usuarios y roles
    type Role = 'Admin' | 'Operador';
    
    interface User {
      id: number;
      nombre: string;
      email: string;
      rol: Role;
      estado: 'Activo' | 'Inactivo';
    }
    
    // Estado para los usuarios
    let users = $state<User[]>([
      { 
        id: 1, 
        nombre: 'Juan Pérez', 
        email: 'juan.perez@ejemplo.com', 
        rol: 'Admin', 
        estado: 'Activo' 
      },
      { 
        id: 2, 
        nombre: 'María López', 
        email: 'maria.lopez@ejemplo.com', 
        rol: 'Operador', 
        estado: 'Activo' 
      },
      { 
        id: 3, 
        nombre: 'Carlos Gómez', 
        email: 'carlos.gomez@ejemplo.com', 
        rol: 'Operador', 
        estado: 'Inactivo' 
      },
      { 
        id: 4, 
        nombre: 'Ana Martínez', 
        email: 'ana.martinez@ejemplo.com', 
        rol: 'Operador', 
        estado: 'Activo' 
      }
    ]);
    
    // Estado para el filtro de búsqueda
    let searchQuery = $state('');
    
    // Estado para el modal de edición/creación
    let showModal = $state(false);
    let editingUser = $state<User | null>(null);
    let newUser = $state<Partial<User>>({
      nombre: '',
      email: '',
      rol: 'Operador',
      estado: 'Activo'
    });
    
    // Estado para mensajes de error en el formulario
    let formErrors = $state({
      nombre: '',
      email: ''
    });
    
    // Función para abrir el modal de creación de usuario
    function openCreateModal(): void {
      editingUser = null;
      newUser = {
        nombre: '',
        email: '',
        rol: 'Operador',
        estado: 'Activo'
      };
      formErrors = { nombre: '', email: '' };
      showModal = true;
    }
    
    // Función para abrir el modal de edición de usuario
    function openEditModal(user: User): void {
      editingUser = user;
      newUser = { ...user };
      formErrors = { nombre: '', email: '' };
      showModal = true;
    }
    
    // Función para cerrar el modal
    function closeModal(): void {
      showModal = false;
    }
    
    // Función para guardar un usuario (crear o editar)
    function saveUser(): void {
      if (editingUser) {
        // Editar usuario existente
        users = users.map(u => 
          u.id === editingUser.id ? { ...u, ...newUser as User } : u
        );
      } else {
        // Crear nuevo usuario
        const currentDate = new Date();
        const formattedDate = `${currentDate.toISOString().split('T')[0]} ${currentDate.toTimeString().split(' ')[0].substring(0, 5)}`;
        
        const newId = users.length > 0 ? Math.max(...users.map(u => u.id)) + 1 : 1;
        
        users = [
          ...users,
          {
            id: newId,
            nombre: newUser.nombre!,
            email: newUser.email!,
            rol: newUser.rol as Role || 'Operador',
            estado: newUser.estado as 'Activo' | 'Inactivo' || 'Activo'
          }
        ];
      }
      
      closeModal();
    }
    
    // Función para cambiar el rol de un usuario
    function changeRole(user: User): void {
      const newRole: Role = user.rol === 'Admin' ? 'Operador' : 'Admin';
      users = users.map(u => 
        u.id === user.id ? { ...u, rol: newRole } : u
      );
    }
    
    // Función para cambiar el estado de un usuario
    function toggleStatus(user: User): void {
      const newStatus = user.estado === 'Activo' ? 'Inactivo' : 'Activo';
      users = users.map(u => 
        u.id === user.id ? { ...u, estado: newStatus } : u
      );
    }
    
    // Función para eliminar un usuario
    function deleteUser(userId: number): void {
      if (confirm('¿Estás seguro de que deseas eliminar este usuario?')) {
        users = users.filter(u => u.id !== userId);
      }
    }
</script>

<div class="min-h-screen bg-[#1a1e2a] text-white">
	<!-- Header -->
	<header class="bg-[#1a1e2a] p-4 border-b border-gray-800 flex items-center justify-between">
		<div class="flex items-center">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-6 w-6 text-blue-400 mr-2"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
				/>
			</svg>
			<h1 class="text-xl font-semibold">Administración de Usuarios</h1>
		</div>
		<button
			onclick={openCreateModal}
			class="bg-blue-600 hover:bg-blue-500 text-white py-2 px-4 rounded flex items-center"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-5 w-5 mr-1"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
			</svg>
			Nuevo Usuario
		</button>
	</header>

	<!-- Barra de filtro -->
	<div class="p-4">
		<div class="relative">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-5 w-5 absolute left-3 top-3 text-gray-400"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
				/>
			</svg>
			<input
				type="text"
				bind:value={searchQuery}
				placeholder="Buscar usuarios por nombre o email..."
				class="w-full bg-[#2d3748] text-white pl-10 p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
			/>
		</div>
	</div>

	<!-- Tabla de usuarios -->
	<div class="overflow-x-auto px-4">
		<table class="w-full border-collapse">
			<!-- Encabezados de tabla -->
			<thead>
				<tr class="bg-[#2d3748] text-gray-300">
					<th class="p-3 text-left font-medium">ID</th>
					<th class="p-3 text-left font-medium">Nombre</th>
					<th class="p-3 text-left font-medium">Email</th>
					<th class="p-3 text-left font-medium">Rol</th>
					<th class="p-3 text-left font-medium">Estado</th>
					<th class="p-3 text-left font-medium">Acciones</th>
				</tr>
			</thead>
			<!-- Cuerpo de la tabla -->
			<tbody>
				{#each users as user}
					<tr class="border-b border-gray-700">
						<td class="p-3">
							<span class="font-medium">#{user.id}</span>
						</td>
						<td class="p-3">
							{user.nombre}
						</td>
						<td class="p-3">
							{user.email}
						</td>
						<td class="p-3">
							<div class="flex items-center">
								<span
									class={`px-2 py-1 rounded text-xs font-medium ${
										user.rol === 'Admin'
											? 'bg-purple-900 text-purple-200'
											: 'bg-blue-900 text-blue-200'
									}`}
								>
									{user.rol}
								</span>
							</div>
						</td>
						<td class="p-3">
							<button
								onclick={() => toggleStatus(user)}
								class={`px-2 py-1 rounded text-xs font-medium ${
									user.estado === 'Activo'
										? 'bg-green-900 text-green-200'
										: 'bg-red-900 text-red-200'
								}`}
							>
								{user.estado}
							</button>
						</td>
						<td class="p-3">
							<div class="flex gap-2">
								<button
									onclick={() => openEditModal(user)}
									class="bg-blue-600 hover:bg-blue-500 text-white text-sm py-1 px-3 rounded"
									title="Editar usuario"
								>
									Editar
								</button>
								<button
									onclick={() => deleteUser(user.id)}
									class="bg-red-600 hover:bg-red-500 text-white text-sm py-1 px-3 rounded"
									title="Eliminar usuario"
								>
									Eliminar
								</button>
							</div>
						</td>
					</tr>
				{/each}

				{#if users.length === 0}
					<tr>
						<td colspan="7" class="p-4 text-center text-gray-400">
							No se encontraron usuarios que coincidan con la búsqueda.
						</td>
					</tr>
				{/if}
			</tbody>
		</table>
	</div>

	<!-- Modal para crear/editar usuario -->
	{#if showModal}
		<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
			<div class="bg-[#1a202c] rounded-lg shadow-lg p-6 w-full max-w-md">
				<h3 class="text-xl font-semibold mb-4">
					{editingUser ? 'Editar Usuario' : 'Nuevo Usuario'}
				</h3>

				<form class="space-y-4">
					<!-- Campo Nombre -->
					<div>
						<label for="nombre" class="block text-sm font-medium text-gray-400 mb-1">Nombre</label>
						<input
							type="text"
							id="nombre"
							bind:value={newUser.nombre}
							class="w-full bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
							class:border-red-500={formErrors.nombre}
						/>
						{#if formErrors.nombre}
							<p class="text-red-500 text-xs mt-1">{formErrors.nombre}</p>
						{/if}
					</div>

					<!-- Campo Email -->
					<div>
						<label for="email" class="block text-sm font-medium text-gray-400 mb-1">Email</label>
						<input
							type="email"
							id="email"
							bind:value={newUser.email}
							class="w-full bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
							class:border-red-500={formErrors.email}
						/>
						{#if formErrors.email}
							<p class="text-red-500 text-xs mt-1">{formErrors.email}</p>
						{/if}
					</div>

					<!-- Campo Rol -->
					<div>
						<label for="rol" class="block text-sm font-medium text-gray-400 mb-1">Rol</label>
						<select
							id="rol"
							bind:value={newUser.rol}
							class="w-full bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
						>
							<option value="Admin">Admin</option>
							<option value="Operador">Operador</option>
						</select>
					</div>

					<!-- Campo Estado -->
					<div>
						<label for="estado" class="block text-sm font-medium text-gray-400 mb-1">Estado</label>
						<select
							id="estado"
							bind:value={newUser.estado}
							class="w-full bg-[#2d3748] text-white p-3 rounded border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
						>
							<option value="Activo">Activo</option>
							<option value="Inactivo">Inactivo</option>
						</select>
					</div>

					<!-- Botones de acción -->
					<div class="flex justify-end gap-3 mt-6">
						<button
							type="button"
							onclick={closeModal}
							class="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded"
						>
							Cancelar
						</button>
						<button
							type="submit"
							class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded"
						>
							{editingUser ? 'Guardar Cambios' : 'Crear Usuario'}
						</button>
					</div>
				</form>
			</div>
		</div>
	{/if}
</div>

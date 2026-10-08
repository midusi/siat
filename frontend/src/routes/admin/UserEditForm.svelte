<script lang="ts">
	import FormField from '$lib/components/FormField.svelte';
	import GlassSelect from '$lib/components/GlassSelect.svelte';
	import PasswordNewConfirm from '$lib/components/PasswordNewConfirm.svelte';
	import Switch from '$lib/components/Switch.svelte';
	import type { Role } from '$lib/types/user';
	import type { FormErrors, UserForm } from '$lib/validation/user';

	let {
		form = $bindable(),
		errors,
		isEditing,
		submitting,
		onsubmit,
		oncancel
	}: {
		form: UserForm;
		errors: FormErrors;
		isEditing: boolean;
		submitting: boolean;
		onsubmit: (event: SubmitEvent) => void;
		oncancel: () => void;
	} = $props();

	const roleItems: { value: Role; label: string }[] = [
		{ value: 'ROLE_ADMIN', label: 'Admin' },
		{ value: 'ROLE_OPERADOR', label: 'Operador' }
	];
</script>

<form class="space-y-4" {onsubmit}>
	<div class="grid grid-cols-2 gap-3">
		<FormField
			id="first_name"
			label="Nombre"
			bind:value={form.first_name}
			error={errors.first_name}
		/>
		<FormField
			id="last_name"
			label="Apellido"
			bind:value={form.last_name}
			error={errors.last_name}
		/>
	</div>

	<FormField id="email" label="Email" type="email" bind:value={form.email} error={errors.email} />

	<FormField
		id="username"
		label="Usuario"
		bind:value={form.username}
		disabled={isEditing}
		error={errors.username}
	/>

	<PasswordNewConfirm
		bind:newPassword={form.password}
		bind:confirmPassword={form.confirm_password}
		errorNew={errors.password}
		errorConfirm={errors.confirm_password}
	/>

	<div>
		<label id="label-rol" for="rol" class="block text-sm mb-1 text-white/80">Rol</label>
		<GlassSelect
			id="rol"
			ariaLabel="Seleccionar rol"
			ariaLabelledby="label-rol"
			items={roleItems}
			value={form.role}
			onChange={(v) => (form.role = v as Role)}
		/>
	</div>

	<div class="flex items-center justify-between">
		<span id="label-estado" class="text-sm text-white/80">Estado</span>
		<Switch
			id="estado"
			labelledby="label-estado"
			bind:checked={form.active}
			onLabel="Activo"
			offLabel="Inactivo"
		/>
	</div>

	{#if errors.general}
		<p class="text-red-400 text-sm">{errors.general}</p>
	{/if}

	<div class="flex justify-end gap-2 pt-2">
		<button type="button" onclick={oncancel} class="glass-button">Cancelar</button>
		<button
			type="submit"
			class="glass-button btn-success disabled:opacity-50"
			disabled={submitting}
		>
			{#if submitting}
				{isEditing ? 'Guardando…' : 'Creando…'}
			{:else}
				{isEditing ? 'Guardar Cambios' : 'Crear Usuario'}
			{/if}
		</button>
	</div>
</form>

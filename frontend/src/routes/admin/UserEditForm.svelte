<script lang="ts">
	import FormField from '$lib/components/FormField.svelte';
	import GlassSelect from '$lib/components/GlassSelect.svelte';
	import PasswordNewConfirm from '$lib/components/PasswordNewConfirm.svelte';
	import { ROLE_LABELS } from '$lib/roles';
	import Switch from '$lib/components/Switch.svelte';

	import type { FormErrors, UserForm } from '$lib/validation/user';
	import type { Role } from '$lib/types/user';
	import type { SelectItem } from '$lib/types/select';

	type Props = {
		errors: FormErrors;
		form: UserForm;
		isEditing: boolean;
		oncancel: () => void;
		onsubmit: (event: SubmitEvent) => void;
		submitting: boolean;
	};

	const ROLE_ITEMS: Array<SelectItem<Role>> = (Object.keys(ROLE_LABELS) as Array<Role>).map(
		(role: Role): SelectItem<Role> => ({ value: role, label: ROLE_LABELS[role] })
	);

	let { errors, form = $bindable(), isEditing, oncancel, onsubmit, submitting }: Props = $props();
</script>

<form class="space-y-4" {onsubmit}>
	<div class="grid grid-cols-2 gap-3">
		<FormField
			id="first_name"
			autocomplete="off"
			label="Nombre"
			bind:value={form.first_name}
			error={errors.first_name}
		/>
		<FormField
			id="last_name"
			autocomplete="off"
			label="Apellido"
			bind:value={form.last_name}
			error={errors.last_name}
		/>
	</div>

	<FormField
		id="email"
		label="Email"
		type="email"
		autocomplete="off"
		bind:value={form.email}
		error={errors.email}
	/>

	<FormField
		id="username"
		autocomplete="off"
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
			items={ROLE_ITEMS}
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

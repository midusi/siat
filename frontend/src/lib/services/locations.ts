import { apiError } from './errors';
import { apiFetch } from '$lib/api';

export type Option = { id: number; name: string };
export type SelectItem = { value: number; label: string };

const fetchOptions = async (path: string, fallback: string): Promise<Option[]> => {
	const res = await apiFetch(path);
	if (!res.ok) {
		throw await apiError(res, fallback);
	}
	return (await res.json()) as Option[];
};

export const fetchDistricts = (provinceId: number): Promise<Option[]> =>
	fetchOptions(`/province/${provinceId}/district`, 'No se pudieron cargar los distritos');

export const fetchLocalities = (districtId: number): Promise<Option[]> =>
	fetchOptions(`/district/${districtId}/locality`, 'No se pudieron cargar las localidades');

export const fetchProvinces = (): Promise<Option[]> =>
	fetchOptions('/province', 'No se pudieron cargar las provincias');

export const toSelectItems = (options: Option[]): SelectItem[] =>
	options
		.slice()
		.sort((a, b) => a.name.localeCompare(b.name, 'es', { sensitivity: 'base' }))
		.map((x) => ({ value: x.id, label: x.name }));

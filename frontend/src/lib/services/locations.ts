import { apiError } from './errors';
import { apiFetch } from '$lib/api';

export type Option = { id: number; name: string };
export type SelectItem = { value: number; label: string };

const fetchOptions = async (path: string, fallback: string): Promise<Array<Option>> => {
	const res: Response = await apiFetch(path);
	if (!res.ok) {
		throw await apiError(res, fallback);
	}
	return (await res.json()) as Array<Option>;
};

export const fetchDistricts = (provinceId: number): Promise<Array<Option>> =>
	fetchOptions(`/province/${provinceId}/district`, 'No se pudieron cargar los distritos');

export const fetchLocalities = (districtId: number): Promise<Array<Option>> =>
	fetchOptions(`/district/${districtId}/locality`, 'No se pudieron cargar las localidades');

export const fetchProvinces = (): Promise<Array<Option>> =>
	fetchOptions('/province', 'No se pudieron cargar las provincias');

export const toSelectItems = (options: Array<Option>): Array<SelectItem> =>
	options
		.slice()
		.sort((first: Option, second: Option): number =>
			first.name.localeCompare(second.name, 'es', { sensitivity: 'base' })
		)
		.map((option: Option): SelectItem => ({ value: option.id, label: option.name }));

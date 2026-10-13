import { apiFetch } from "$lib/api";
import { apiError } from "./errors";

const PROFILE_API: string = '/user/me';

export const changePassword = async (current_password: string, new_password: string, confirm_password: string): Promise<void> => {
    const res = await apiFetch(`${PROFILE_API}change-password`, {
        method: 'POST',
        body: JSON.stringify({ current_password, new_password, confirm_password })
    });
    if (!res.ok) {
        throw await apiError(res, 'No se pudo cambiar la contraseña');
    }
}
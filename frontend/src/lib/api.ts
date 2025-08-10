export const BACKEND_BASE = '/api';

export type ApiInit = RequestInit & { rawUrl?: string };

export async function apiFetch(path: string, init: ApiInit = {}): Promise<Response> {
    const url = init.rawUrl === 'absolute' ? path : `${BACKEND_BASE}${path}`;
    const isFormData = typeof FormData !== 'undefined' && init.body instanceof FormData;
    const headers: Record<string, string> = {
        ...(init.headers as Record<string, string> | undefined)
    };
    if (!isFormData) {
        headers['Content-Type'] = headers['Content-Type'] ?? 'application/json';
    }
    const res = await fetch(url, {
        credentials: 'include',
        ...init,
        headers,
    } as RequestInit);
    return res;
}

import { BACKEND_URL } from '$lib/constants';

const CSRF_HEADER: string = 'X-CSRF-Token';

export const apiFetch = (path: string, init: RequestInit = {}): Promise<Response> => {
	const headers: Headers = new Headers(init.headers);
	if (typeof init.body === 'string' && !headers.has('Content-Type')) {
		headers.set('Content-Type', 'application/json');
	}
	const method: string = (init.method ?? 'GET').toUpperCase();
	if (method !== 'GET' && method !== 'HEAD' && !headers.has(CSRF_HEADER)) {
		headers.set(CSRF_HEADER, '1');
	}
	return fetch(`${BACKEND_URL}${path}`, { ...init, headers });
};

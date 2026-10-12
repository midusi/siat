const BACKEND_BASE: string = '/api';
const CSRF_HEADER: string = 'X-CSRF-Token';

export const apiFetch = (path: string, init: RequestInit = {}): Promise<Response> => {
	const headers = new Headers(init.headers);
	if (typeof init.body === 'string' && !headers.has('Content-Type')) {
		headers.set('Content-Type', 'application/json');
	}
	const method = (init.method ?? 'GET').toUpperCase();
	if (method !== 'GET' && method !== 'HEAD' && !headers.has(CSRF_HEADER)) {
		headers.set(CSRF_HEADER, '1');
	}
	return fetch(`${BACKEND_BASE}${path}`, { ...init, headers });
};

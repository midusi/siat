import type { RequestHandler } from './$types';

// Optional proxy endpoint to the backend logout to keep same origin if needed
export const POST: RequestHandler = async ({ fetch }) => {
	const res = await fetch('http://127.0.0.1:8000/auth/logout', {
		method: 'POST',
		headers: { 'X-CSRF-Token': '1' },
		credentials: 'include'
	} as RequestInit);
	return new Response(null, { status: res.status });
};

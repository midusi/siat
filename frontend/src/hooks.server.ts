// src/hooks.server.ts
import type { Handle, HandleFetch } from '@sveltejs/kit';

// Hydrate locals.user by querying backend via same-origin proxy /api/auth/me
export const handle: Handle = async ({ event, resolve }) => {
	event.locals.user = null;
	// Avoid recursion: skip hydration when the current request already targets the /api proxy
	if (event.url.pathname.startsWith('/api')) {
		return resolve(event);
	}
	try {
		const res = await event.fetch('/api/auth/me', {
			credentials: 'include'
		} as RequestInit);
		if (res.ok) {
			const data = await res.json();
			event.locals.user = (data.user ?? data) as App.Locals['user'];
		}
	} catch {
		// Ignore errors -> treat as unauthenticated
	}
	return resolve(event);
};

// Forward cookies to the backend in server-side fetches
export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
	const cookie = event.request.headers.get('cookie');
	if (cookie) request.headers.set('cookie', cookie);
	return fetch(request);
};

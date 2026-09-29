import type { Handle } from '@sveltejs/kit';

export const handle: Handle = async ({ event, resolve }) => {
	event.locals.user = null;
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
	}
	return resolve(event);
};

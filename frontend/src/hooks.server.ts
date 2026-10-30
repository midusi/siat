import { BACKEND_URL, BUCKET_URL } from '$lib/constants';

import type { Handle } from '@sveltejs/kit';

const SKIP_AUTH_PREFIXES = [BACKEND_URL, BUCKET_URL];

export const handle: Handle = async ({ event, resolve }) => {
	event.locals.user = null;
	const pathname = event.url.pathname;

	const excludeAuth: boolean = SKIP_AUTH_PREFIXES.some(
		(exclude) => pathname.startsWith(exclude + '/') || pathname === exclude
	);

	if (excludeAuth) {
		return resolve(event);
	}

	try {
		const res = await event.fetch(`${BACKEND_URL}/auth/me`);
		if (res.ok) {
			const data = await res.json();
			event.locals.user = data as App.Locals['user'];
		}
	} catch (e) {
		console.error('No se pudo obtener el usuario actual', e);
	}
	return resolve(event);
};

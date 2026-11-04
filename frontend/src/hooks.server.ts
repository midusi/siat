import { BACKEND_URL, BUCKET_URL } from '$lib/constants';

import type { Handle } from '@sveltejs/kit';
import type { User } from '$lib/types/user';

const SKIP_AUTH_PREFIXES: Array<string> = [BACKEND_URL, BUCKET_URL];

export const handle: Handle = async ({ event, resolve }) => {
	event.locals.user = null;
	const pathname: string = event.url.pathname;

	const excludeAuth: boolean = SKIP_AUTH_PREFIXES.some(
		(exclude) => pathname.startsWith(`${exclude}/`) || pathname === exclude
	);

	if (excludeAuth) {
		return resolve(event);
	}

	try {
		const res: Response = await event.fetch(`${BACKEND_URL}/auth/me`);
		if (res.ok) {
			event.locals.user = (await res.json()) as User;
		}
	} catch (e) {
		console.error('No se pudo obtener el usuario actual', e);
	}
	return resolve(event);
};

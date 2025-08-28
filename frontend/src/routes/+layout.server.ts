import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';

const PUBLIC_ROUTES = new Set(['/login']);

export const load: LayoutServerLoad = async ({ locals, url }) => {
	const isPublic = PUBLIC_ROUTES.has(url.pathname);
	const user = locals.user;
	if (!isPublic && !user) {
		throw redirect(302, `/login?next=${encodeURIComponent(url.pathname)}`);
	}
	return { user };
};

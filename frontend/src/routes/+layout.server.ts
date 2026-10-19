import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';

const PUBLIC_ROUTES = new Set(['/login']);

export const load: LayoutServerLoad = ({ locals, url }) => {
	const isPublic = PUBLIC_ROUTES.has(url.pathname);
	const user = locals.user;
	if (!isPublic && !user) {
		redirect(302, `/login?next=${encodeURIComponent(url.pathname + url.search)}`);
	}
	return { user };
};

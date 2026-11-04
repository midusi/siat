import { LOGIN_PATH } from '$lib/constants';
import { redirect } from '@sveltejs/kit';
import { REDIRECT_CODE } from '$lib/redirect';

import type { LayoutServerLoad } from './$types';
import type { User } from '$lib/types/user';

const PUBLIC_ROUTES: Set<string> = new Set([LOGIN_PATH]);

export const load: LayoutServerLoad = ({ locals, url }) => {
	const isPublic: boolean = PUBLIC_ROUTES.has(url.pathname);
	const user: User | null = locals.user;
	if (!isPublic && !user) {
		redirect(REDIRECT_CODE, `${LOGIN_PATH}?next=${encodeURIComponent(url.pathname + url.search)}`);
	}
	return { user };
};

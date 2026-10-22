import { redirect } from '@sveltejs/kit';
import { REDIRECT_CODE } from '$lib/redirect';

import type { PageServerLoad } from './$types';
import type { User } from '$lib/types/user';

export const load: PageServerLoad = ({ locals }) => {
	const user: User | null = locals.user;
	if (!user) {
		redirect(REDIRECT_CODE, '/login');
	}
	if (user.role !== 'ROLE_ADMIN') {
		redirect(REDIRECT_CODE, '/');
	}
	return { user };
};

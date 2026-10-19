import type { PageServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';

const REDIRECT_CODE: number = 302;

export const load: PageServerLoad = async ({ locals }) => {
	const user = locals.user;
	if (!user) {
		throw redirect(REDIRECT_CODE, '/login');
	}
	if (user.role !== 'ROLE_ADMIN') {
		throw redirect(REDIRECT_CODE, '/');
	}
	return { user };
};

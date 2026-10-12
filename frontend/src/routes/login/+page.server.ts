import type { PageServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';
import { safeNext } from '$lib/redirect';

export const load: PageServerLoad = async ({ locals, url }) => {
	if (locals.user) {
		redirect(302, safeNext(url.searchParams.get('next')));
	}
	return {};
};

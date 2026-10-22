import { redirect } from '@sveltejs/kit';
import { REDIRECT_CODE, safeNext } from '$lib/redirect';

import type { PageServerLoad } from './$types';

export const load: PageServerLoad = ({ locals, url }) => {
	if (locals.user) {
		redirect(REDIRECT_CODE, safeNext(url.searchParams.get('next')));
	}
	return {};
};

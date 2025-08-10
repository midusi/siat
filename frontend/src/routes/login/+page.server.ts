import type { PageServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ locals, url }) => {
    if (locals.user) {
        const next = url.searchParams.get('next') ?? '/';
        throw redirect(302, next);
    }
    return {};
};

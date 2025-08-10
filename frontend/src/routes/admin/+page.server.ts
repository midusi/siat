import type { PageServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ locals }) => {
    const user = locals.user;
    if (!user) throw redirect(302, '/login');
    if (user.role !== 'ROLE_ADMIN') throw redirect(302, '/');
    return { user };
};

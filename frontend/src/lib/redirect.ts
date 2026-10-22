export const REDIRECT_CODE: number = 302;

export const safeNext = (next: string | null): string =>
	next?.startsWith('/') && !next.startsWith('//') ? next : '/';

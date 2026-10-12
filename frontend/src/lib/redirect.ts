export const safeNext = (next: string | null): string =>
	next?.startsWith('/') && !next.startsWith('//') ? next : '/';

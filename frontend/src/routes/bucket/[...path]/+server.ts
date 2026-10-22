import { env } from '$env/dynamic/private';
import { error } from '@sveltejs/kit';

import type { RequestEvent, RequestHandler } from './$types';

const proxy = async ({ request, params }: RequestEvent): Promise<Response> => {
	if (!env.MINIO_URL) {
		console.error('MINIO_URL no está definida');
		error(500, 'MINIO mal configurado');
	}
	const url: string = `${env.MINIO_URL}/${params.path}`;

	const headers: Headers = new Headers(request.headers);
	headers.delete('host');
	headers.delete('connection');

	try {
		const res: Response = await fetch(url, {
			method: request.method,
			headers,
			redirect: 'manual',
			signal: request.signal
		});
		return new Response(res.body, { status: res.status, headers: res.headers });
	} catch (e) {
		if (request.signal.aborted) {
			return new Response(null, { status: 499 });
		}
		console.error(`MINIO error: ${request.method} ${url}`, e);
		error(502, 'MINIO no disponible');
	}
};

export const GET: RequestHandler = proxy;

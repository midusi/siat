import type { RequestHandler, RequestEvent } from './$types';
import { error } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

const proxy = async ({ request, params }: RequestEvent): Promise<Response> => {
	if (!env.BACKEND_URL) {
		console.error('BACKEND_URL no está definida');
		error(500, 'Proxy mal configurado');
	}
	const url = `${env.BACKEND_URL}/${params.path}`;

	const headers = new Headers(request.headers);
	headers.delete('host');
	headers.delete('connection');
	const body = ['GET', 'HEAD'].includes(request.method) ? undefined : request.body;

	const init: RequestInit & { duplex: 'half' } = {
		method: request.method,
		headers,
		body,
		redirect: 'manual',
		signal: request.signal,
		duplex: 'half'
	};

	let res: Response;
	try {
		res = await fetch(url, init);
	} catch (e) {
		if (request.signal.aborted) {
			return new Response(null, { status: 499 });
		}
		console.error(`Proxy error: ${request.method} ${url}`, e);
		error(502, 'Backend no disponible');
	}

	const responseHeaders = new Headers(res.headers);
	responseHeaders.delete('content-encoding');
	responseHeaders.delete('content-length');
	responseHeaders.delete('set-cookie');

	for (const sc of res.headers.getSetCookie()) {
		responseHeaders.append('set-cookie', sc.replace(/;\s*Domain=[^;]+/i, ''));
	}

	return new Response(res.body, { status: res.status, headers: responseHeaders });
};

export const fallback: RequestHandler = proxy;

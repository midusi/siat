import type { RequestHandler } from './$types';

const BACKEND_BASE = 'http://127.0.0.1:8000';

async function proxy(event: Parameters<RequestHandler>[0]): Promise<Response> {
    const { request, params, fetch } = event;
    const targetPath = params.path as string; // catch-all
    const url = `${BACKEND_BASE}/${targetPath}`;

    const headers = new Headers(request.headers);
    // Ensure cookies are forwarded
    const cookie = request.headers.get('cookie');
    if (cookie) headers.set('cookie', cookie);

    const body = ['GET', 'HEAD'].includes(request.method)
        ? undefined
        : await request.arrayBuffer();

    const res = await fetch(url, {
        method: request.method,
        headers,
        body,
        redirect: 'manual'
    } as RequestInit);

    // Build response and forward Set-Cookie headers
    const responseHeaders = new Headers(res.headers);
    // Remove content-encoding if any to avoid issues
    responseHeaders.delete('content-encoding');

    // Forward multiple Set-Cookie headers with wide compatibility
    // 1) undici provides getSetCookie()
    const anyHeaders = res.headers as any;
    let setCookies: string[] | undefined = anyHeaders?.getSetCookie?.();
    // 2) node-fetch style raw()
    if (!setCookies) {
        const raw = anyHeaders?.raw?.();
        if (raw && Array.isArray(raw['set-cookie'])) {
            setCookies = raw['set-cookie'];
        }
    }
    // 3) Fallback: single header
    if (!setCookies) {
        const single = res.headers.get('set-cookie');
        if (single) setCookies = [single];
    }
    if (setCookies && setCookies.length) {
        responseHeaders.delete('set-cookie');
        for (let sc of setCookies) {
            // Strip Domain attribute so cookie is set for frontend host
            sc = sc.replace(/;\s*Domain=[^;]+/i, '');
            responseHeaders.append('set-cookie', sc);
        }
    }

    const status = res.status;
    // For 204/304, do not include a body
    if (status === 204 || status === 304) {
        return new Response(null, { status, headers: responseHeaders });
    }

    const buf = await res.arrayBuffer();
    return new Response(buf, { status, headers: responseHeaders });
}

export const GET: RequestHandler = async (e) => proxy(e);
export const POST: RequestHandler = async (e) => proxy(e);
export const PUT: RequestHandler = async (e) => proxy(e);
export const PATCH: RequestHandler = async (e) => proxy(e);
export const DELETE: RequestHandler = async (e) => proxy(e);

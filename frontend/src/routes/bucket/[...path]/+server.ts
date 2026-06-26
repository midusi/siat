import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/private';

// Proxy to MinIO (or S3-compatible) running locally on 127.0.0.1:9000
const BUCKET_BASE = env.MINIO_URL || 'http://127.0.0.1:9000';

async function proxy(event: Parameters<RequestHandler>[0]): Promise<Response> {
    const { request, params } = event;
    const targetPath = params.path as string; // catch-all
    const targetUrl = `${BUCKET_BASE}/${targetPath}`;

    // Forward request headers (including Range for video streaming)
    const headers = new Headers(request.headers);

    // For GET/HEAD, no body. For others, stream the body directly
    const body = ['GET', 'HEAD'].includes(request.method)
        ? undefined
        : request.body;

    const res = await globalThis.fetch(targetUrl, {
        method: request.method,
        headers,
        body,
        redirect: 'manual',
        // @ts-ignore
        duplex: 'half'
    });

    // Stream the body back to the client, preserving status and headers
    const responseHeaders = new Headers(res.headers);
    // Some proxies add content-encoding; leave as-is to preserve range support

    return new Response(res.body, {
        status: res.status,
        headers: responseHeaders
    });
}

export const GET: RequestHandler = async (e) => proxy(e);
export const HEAD: RequestHandler = async (e) => proxy(e);
export const POST: RequestHandler = async (e) => proxy(e);
export const PUT: RequestHandler = async (e) => proxy(e);
export const PATCH: RequestHandler = async (e) => proxy(e);
export const DELETE: RequestHandler = async (e) => proxy(e);

// src/hooks.server.ts
import type { HandleFetch } from '@sveltejs/kit';

export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
  const cookie = event.request.headers.get('cookie');
  if (cookie) {
    request.headers.set('cookie', cookie);
  }
  return fetch(request);
};

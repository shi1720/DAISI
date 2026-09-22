import type { Session } from './types';

let csrfToken: string | null = null;
export function useSessionToken(session: Session) { csrfToken = session.csrf_token; }

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.name = 'ApiError'; this.status = status; }
}

async function request(path: string, options: RequestInit = {}): Promise<Response> {
  const method = options.method ?? 'GET';
  const headers = new Headers(options.headers);
  if (options.body) headers.set('Content-Type', 'application/json');
  if (method !== 'GET' && csrfToken) headers.set('X-CSRF-Token', csrfToken);
  let response: Response;
  try { response = await fetch(`/api${path}`, { ...options, headers, credentials: 'same-origin' }); }
  catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error;
    throw new ApiError('Unable to reach the service. Check your connection and try again.', 0);
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail;
    const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((x: { msg: string }) => x.msg).join('; ') : `The request could not be completed (${response.status}).`;
    if (response.status === 401) { csrfToken = null; window.dispatchEvent(new Event('hawkerbridge:session-expired')); }
    throw new ApiError(message, response.status);
  }
  return response;
}
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await request(path, options);
  if (response.status === 204) return undefined as T;
  try { return await response.json() as T; }
  catch { throw new ApiError('The service returned an unreadable response. Refresh and try again.', response.status); }
}
export async function apiBlob(path: string, options: RequestInit = {}): Promise<Blob> {
  return (await request(path, options)).blob();
}
export function post<T>(path: string, body: unknown, signal?: AbortSignal) {
  return api<T>(path, { method: 'POST', body: JSON.stringify(body), signal });
}
export const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong. Please try again.';

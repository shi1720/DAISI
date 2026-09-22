import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, apiBlob, post, useSessionToken } from './api';

describe('session-aware API transport', () => {
  beforeEach(() => useSessionToken({user:null,csrf_token:'session-token',auth_mode:'local'}));
  afterEach(() => vi.unstubAllGlobals());
  it('sends the session CSRF token and same-origin credentials on mutations', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({id:'saved'}),{status:200}));
    vi.stubGlobal('fetch',fetchMock);
    expect(await post('/plans',{title:'Community proposal'})).toEqual({id:'saved'});
    const [url,request] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/plans');
    expect(request.credentials).toBe('same-origin');
    expect(request.headers.get('X-CSRF-Token')).toBe('session-token');
    expect(JSON.parse(request.body)).toEqual({title:'Community proposal'});
  });
  it('exposes useful validation errors instead of pretending a failed request succeeded', async () => {
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:[{msg:'Budget must be nonnegative'},{msg:'Choose a valid date'}]}),{status:422})));
    await expect(post('/optimise',{})).rejects.toThrow('Budget must be nonnegative; Choose a valid date');
  });
  it('clears expired application state through a session-expired event', async () => {
    const expired = vi.fn();window.addEventListener('hawkerbridge:session-expired',expired);
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'Session expired'}),{status:401})));
    await expect(api('/plans')).rejects.toThrow('Session expired');expect(expired).toHaveBeenCalledOnce();
    window.removeEventListener('hawkerbridge:session-expired',expired);
  });
  it('applies session-expiry handling to downloads and clears the old CSRF token', async () => {
    const expired = vi.fn();window.addEventListener('hawkerbridge:session-expired',expired);
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({detail:'Session expired'}),{status:401}))
      .mockResolvedValueOnce(new Response(JSON.stringify({user:null}),{status:200}));
    vi.stubGlobal('fetch',fetchMock);
    await expect(apiBlob('/plans/example/export?format=pdf')).rejects.toThrow('Session expired');
    expect(expired).toHaveBeenCalledOnce();
    await post('/auth/login',{});
    expect(fetchMock.mock.calls[1][1].headers.has('X-CSRF-Token')).toBe(false);
    window.removeEventListener('hawkerbridge:session-expired',expired);
  });
  it('explains an unexpected HTML service response without leaking a parser error', async () => {
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response('<html>Offline</html>',{status:200})));
    await expect(api('/auth/session')).rejects.toThrow('The service returned an unreadable response');
  });
  it('handles a successful no-content delete', async () => {
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(null,{status:204})));
    await expect(api('/plans/example',{method:'DELETE'})).resolves.toBeUndefined();
  });
});

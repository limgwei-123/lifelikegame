import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { once } from 'node:events';
import { test } from 'node:test';
import { ApiClient, ApiError } from '../src/api/client.ts';

test('HTTP client sends bearer/body and handles 204 without JSON parsing', async () => {
  const received: { auth?: string; body: string }[] = [];
  const server = createServer(async (req, res) => {
    let body = '';
    for await (const chunk of req) body += chunk;
    received.push({ auth: req.headers.authorization, body });
    res.writeHead(204).end();
  }).listen(0, '127.0.0.1');
  await once(server, 'listening');
  try {
    const port = (server.address() as { port: number }).port;
    const api = new ApiClient(`http://127.0.0.1:${port}`, () => ({ token: 'test-token', revision: 3 }), () => {});
    assert.equal(await api.request('/anything', { method: 'POST', body: { title: 'Hello' } }), null);
    assert.deepEqual(received, [{ auth: 'Bearer test-token', body: '{"title":"Hello"}' }]);
  } finally { server.close(); server.closeAllConnections(); }
});

test('only an authenticated 401 expires its captured session; 403/422/429 remain errors', async () => {
  const expired: number[] = [];
  const api = new ApiClient('https://api.example.test', () => ({ token: 'old-token', revision: 5 }),
    context => { expired.push(context.revision); }, async url => {
      const code = Number(String(url).split('/').at(-1));
      return new Response(JSON.stringify({ code: 'DENIED', detail: 'private error' }), {
        status: code, headers: { 'Content-Type': 'application/json', 'Retry-After': '30' },
      });
    });
  for (const status of [403, 422, 429, 401]) {
    await assert.rejects(api.request(`/${status}`), error => error instanceof ApiError && error.status === status);
  }
  assert.deepEqual(expired, [5]);
  await assert.rejects(api.request('/401', { auth: false }), ApiError);
  assert.deepEqual(expired, [5]);
  await assert.rejects(api.request('/429'), error => error instanceof ApiError && error.retryAfter === 30);
});

test('validation errors never keep raw request/password input', async () => {
  const api = new ApiClient('https://api.example.test', () => null, () => {}, async () =>
    new Response(JSON.stringify({ detail: [{ loc: ['body', 'password'], type: 'string_too_short', input: 'private-password' }] }),
      { status: 422, headers: { 'Content-Type': 'application/json' } }));
  await assert.rejects(api.request('/auth/signup', { auth: false }), error => {
    assert.ok(error instanceof ApiError);
    assert.ok(!JSON.stringify(error).includes('private-password'));
    assert.ok(!error.message.includes('private-password'));
    return true;
  });
});

test('network failures and malformed success responses become usable errors', async () => {
  const api = new ApiClient('https://api.example.test', () => null, () => {}, async () => { throw new TypeError('network'); });
  await assert.rejects(api.request('/health'), error => error instanceof ApiError && error.code === 'NETWORK');
  const broken = new ApiClient('https://api.example.test', () => null, () => {}, async () =>
    new Response('{invalid', { headers: { 'Content-Type': 'application/json' } }));
  await assert.rejects(broken.request('/health'), error => error instanceof ApiError && error.code === 'INVALID_RESPONSE');
});

test('task conflicts use task feedback while duplicate signup keeps the email-specific message', async () => {
  const api = new ApiClient('https://api.example.test', () => ({ token: 'token', revision: 1 }), () => {}, async () =>
    new Response(JSON.stringify({ code: 'CONFLICT' }), { status: 409 }));
  await assert.rejects(api.request('/task_instances/1/complete'), error => error instanceof ApiError && !error.message.includes('邮箱') && error.message.includes('刷新'));
  await assert.rejects(api.request('/auth/signup', { auth: false }), error => error instanceof ApiError && error.message.includes('邮箱'));
});

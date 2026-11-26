import assert from 'node:assert/strict';
import { test } from 'node:test';
import { SessionController } from '../src/session/controller.ts';
import type { TokenStore } from '../src/session/types.ts';

const user = { id: '806bcba0-7adc-4c6f-88f0-b824ab827431', email: 'player@example.com',
  current_value: 0, display_name: null, avatar_key: 'leaf', timezone: 'Asia/Kuala_Lumpur' };
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { 'Content-Type': 'application/json' },
});
function storage(initial: string | null = null): TokenStore & { value: string | null } {
  return { value: initial, async read() { return this.value; }, async write(value) { this.value = value; } };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(yes => { resolve = yes; });
  return { promise, resolve };
}
const normalFetch: typeof fetch = async url => String(url).endsWith('/auth/login') ? json({ access_token: 'valid-token', token_type: 'bearer' }) : json(user);

test('login validates me, persists only token, restores and logs out', async () => {
  const store = storage();
  const session = new SessionController(store, 'https://api.example.test', normalFetch);
  await session.restore();
  assert.equal(session.getSnapshot().status, 'signedOut');
  assert.equal(await session.signIn(user.email, 'password123'), true);
  assert.equal(session.getSnapshot().user?.email, user.email);
  assert.equal(store.value, 'valid-token');
  assert.ok(!JSON.stringify(session.getSnapshot()).includes('password123'));
  const restored = new SessionController(store, 'https://api.example.test', normalFetch);
  await restored.restore();
  assert.equal(restored.getSnapshot().status, 'signedIn');
  await restored.logout();
  assert.equal(store.value, null);
  assert.equal(restored.getSnapshot().user, null);
});

test('wrong credentials do not create a stored session', async () => {
  const store = storage();
  const session = new SessionController(store, 'https://api.example.test', async () => json({ detail: 'Invalid credentials' }, 401));
  assert.equal(await session.signIn(user.email, 'incorrect'), false);
  assert.equal(store.value, null);
  assert.equal(session.getSnapshot().status, 'signedOut');
  assert.ok(session.getSnapshot().error);
});

test('expired stored token clears storage; temporary outage keeps it available for retry', async () => {
  const expired = storage('expired');
  const session = new SessionController(expired, 'https://api.example.test', async () => json({}, 401));
  await session.restore();
  assert.equal(session.getSnapshot().status, 'signedOut');
  assert.equal(expired.value, null);
  const offline = storage('still-valid');
  let available = false;
  const retry = new SessionController(offline, 'https://api.example.test', async () => {
    if (!available) throw new TypeError('offline');
    return json(user);
  });
  await retry.restore();
  assert.equal(retry.getSnapshot().status, 'unavailable');
  assert.equal(offline.value, 'still-valid');
  available = true;
  await retry.restore();
  assert.equal(retry.getSnapshot().status, 'signedIn');
});

test('late login response cannot restore a logged-out session', async () => {
  const reply = deferred<Response>();
  const store = storage();
  const session = new SessionController(store, 'https://api.example.test', async url =>
    String(url).endsWith('/auth/login') ? reply.promise : json(user));
  const signingIn = session.signIn(user.email, 'password123');
  await session.logout();
  reply.resolve(json({ access_token: 'old-token', token_type: 'bearer' }));
  await signingIn;
  assert.equal(session.getSnapshot().status, 'signedOut');
  assert.equal(store.value, null);
});

test('logout queued behind an in-flight token save wins on disk too', async () => {
  const started = deferred<void>(), release = deferred<void>();
  const store = storage();
  store.write = async value => {
    if (value) { started.resolve(); await release.promise; }
    store.value = value;
  };
  const session = new SessionController(store, 'https://api.example.test', normalFetch);
  const signingIn = session.signIn(user.email, 'password123');
  await started.promise;
  const signingOut = session.logout();
  release.resolve();
  await Promise.all([signingIn, signingOut]);
  assert.equal(store.value, null);
  assert.equal(session.getSnapshot().status, 'signedOut');
});

test('a stale 401 cannot expire a newer login even if the backend reused the token', async () => {
  const late = deferred<Response>();
  const store = storage();
  const session = new SessionController(store, 'https://api.example.test', async (url, init) =>
    String(url).endsWith('/slow') ? late.promise : normalFetch(url, init));
  await session.signIn(user.email, 'password123');
  const oldRequest = session.api.request('/slow').catch(() => {});
  await session.logout();
  await session.signIn(user.email, 'password123');
  late.resolve(json({}, 401));
  await oldRequest;
  assert.equal(session.getSnapshot().status, 'signedIn');
  assert.equal(store.value, 'valid-token');
});

test('storage write failures never report login or logout success', async () => {
  const store = storage();
  store.write = async () => { throw new Error('storage unavailable'); };
  const session = new SessionController(store, 'https://api.example.test', normalFetch);
  assert.equal(await session.signIn(user.email, 'password123'), false);
  assert.equal(session.getSnapshot().status, 'signedOut');
  const stuck = storage('valid-token');
  const restored = new SessionController(stuck, 'https://api.example.test', normalFetch);
  await restored.restore();
  stuck.write = async () => { throw new Error('cannot clear'); };
  await restored.logout();
  assert.equal(restored.getSnapshot().status, 'unavailable');
  assert.equal(restored.getSnapshot().user, null);
  assert.equal(restored.getSnapshot().recovery, 'clear');
});

test('registration does not log in or persist the password', async () => {
  const store = storage();
  const session = new SessionController(store, 'https://api.example.test', async () => json(user, 201));
  assert.equal(await session.signUp(user.email, 'password123'), true);
  assert.equal(session.getSnapshot().status, 'signedOut');
  assert.equal(store.value, null);
});

test('a newer failed login must not cancel an already requested logout clear', async () => {
  const store = storage('valid-token');
  let wrong = false;
  const session = new SessionController(store, 'https://api.example.test', async (url, init) =>
    wrong && String(url).endsWith('/auth/login') ? json({}, 401) : normalFetch(url, init));
  await session.restore();
  const logout = session.logout();
  wrong = true;
  const failed = session.signIn(user.email, 'wrong');
  await Promise.all([logout, failed]);
  assert.equal(store.value, null);
  assert.equal(session.getSnapshot().status, 'signedOut');
});

test('failed delayed logout clear cannot be hidden by a concurrent failed login', async () => {
  const clearing = deferred<void>(), release = deferred<void>();
  const store = storage('valid-token');
  let wrong = false;
  const session = new SessionController(store, 'https://api.example.test', async (url, init) =>
    wrong && String(url).endsWith('/auth/login') ? json({}, 401) : normalFetch(url, init));
  await session.restore();
  store.write = async () => { clearing.resolve(); await release.promise; throw new Error('cannot clear'); };
  const logout = session.logout();
  await clearing.promise;
  wrong = true;
  assert.equal(await session.signIn(user.email, 'wrong'), false);
  release.resolve();
  await logout;
  assert.equal(session.getSnapshot().status, 'unavailable');
  assert.equal(session.getSnapshot().recovery, 'clear');
  assert.equal(await session.signIn(user.email, 'wrong'), false);
  store.write = async value => { store.value = value; };
  await session.restore();
  assert.equal(store.value, null);
  assert.equal(session.getSnapshot().status, 'signedOut');
});

test('a delayed profile response cannot replace a newer account', async () => {
  const profile = deferred<Response>(), started = deferred<void>();
  const other = { ...user, id: 'second-user', email: 'second@example.com' };
  const store = storage();
  const session = new SessionController(store, 'https://api.example.test', async (url, init) => {
    if (String(url).endsWith('/auth/login')) {
      return json({ access_token: String(init?.body).includes(other.email) ? 'second-token' : 'first-token' });
    }
    if (new Headers(init?.headers).get('Authorization') === 'Bearer first-token') {
      started.resolve(); return profile.promise;
    }
    return json(other);
  });
  const first = session.signIn(user.email, 'password123');
  await started.promise;
  await session.signIn(other.email, 'password123');
  profile.resolve(json(user));
  await first;
  assert.equal(session.getSnapshot().user?.id, other.id);
  assert.equal(store.value, 'second-token');
});

test('storage read failure offers retry without reporting a signed-in account', async () => {
  const store = storage('valid-token');
  const read = store.read;
  store.read = async () => { throw new Error('device locked'); };
  const session = new SessionController(store, 'https://api.example.test', normalFetch);
  await session.restore();
  assert.equal(session.getSnapshot().status, 'unavailable');
  assert.equal(session.getSnapshot().user, null);
  store.read = read;
  await session.restore();
  assert.equal(session.getSnapshot().status, 'signedIn');
});

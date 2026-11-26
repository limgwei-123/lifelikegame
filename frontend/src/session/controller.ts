import { ApiClient, ApiError, type AuthContext } from '../api/client';
import { isUser } from '../api/types';
import type { SessionSnapshot, TokenStore } from './types';

const initial: SessionSnapshot = { status: 'restoring', user: null, pending: false, error: null, notice: null };

export class SessionController {
  private snapshot: SessionSnapshot = initial;
  private revision = 0;
  private token: string | null = null;
  private readonly listeners = new Set<() => void>();
  private writes: Promise<void> = Promise.resolve();
  private authRequest?: AbortController;
  readonly api: ApiClient;

  constructor(private readonly store: TokenStore, baseUrl: string, fetcher: typeof fetch = fetch) {
    this.api = new ApiClient(baseUrl,
      () => this.token ? { token: this.token, revision: this.revision } : null,
      context => this.expire(context), fetcher);
  }

  getSnapshot = () => this.snapshot;
  getServerSnapshot = () => initial;
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  private publish(next: SessionSnapshot) { this.snapshot = next; this.listeners.forEach(listener => listener()); }
  private begin() {
    this.authRequest?.abort();
    this.authRequest = new AbortController();
    return ++this.revision;
  }
  private async persist(revision: number, token: string | null) {
    const next = this.writes.catch(() => {}).then(async () => {
      // A requested clear must still run if another login starts. It is queued
      // before that login's save, so logout cannot leave an old account on disk.
      if (token === null || revision === this.revision) await this.store.write(token);
    });
    this.writes = next;
    await next;
    return revision === this.revision;
  }
  private errorMessage(error: unknown) {
    return error instanceof ApiError ? error.message : '暂时无法保存登录状态，请重试。';
  }
  private async expire(context: AuthContext) {
    if (context.revision !== this.revision || context.token !== this.token) return;
    await this.logout('登录已失效，请重新登录。');
  }

  restore = async () => {
    if (this.snapshot.recovery === 'clear') return this.logout();
    const revision = this.begin();
    this.token = null;
    this.publish({ ...initial });
    try {
      const stored = await this.store.read();
      if (revision !== this.revision) return;
      if (!stored) {
        this.publish({ status: 'signedOut', user: null, pending: false, error: null, notice: null });
        return;
      }
      this.token = stored;
      const user = await this.api.request('/users/me', { signal: this.authRequest?.signal });
      if (revision !== this.revision) return;
      if (!isUser(user)) throw new ApiError(502, 'INVALID_RESPONSE', '无法读取账户资料，请稍后重试。');
      this.publish({ status: 'signedIn', user, pending: false, error: null, notice: null });
    } catch (error) {
      if (revision !== this.revision) return;
      this.token = null;
      this.publish({ status: 'unavailable', user: null, pending: false, recovery: 'restore',
        error: error instanceof ApiError ? error.message : '无法读取登录状态，请重试。', notice: null });
    }
  };

  signIn = async (email: string, password: string): Promise<boolean> => {
    if (this.snapshot.recovery === 'clear') return false;
    const revision = this.begin();
    this.token = null;
    this.publish({ status: 'signedOut', user: null, pending: true, error: null, notice: null });
    try {
      const result = await this.api.request<{ access_token?: unknown }>('/auth/login', {
        method: 'POST', body: { email: email.trim(), password }, auth: false, signal: this.authRequest?.signal,
      });
      if (revision !== this.revision) return false;
      if (typeof result?.access_token !== 'string' || !result.access_token) {
        throw new ApiError(502, 'INVALID_RESPONSE', '登录返回异常，请重试。');
      }
      const token = result.access_token;
      const user = await this.api.request('/users/me', { context: { token, revision }, signal: this.authRequest?.signal });
      if (revision !== this.revision) return false;
      if (!isUser(user)) throw new ApiError(502, 'INVALID_RESPONSE', '无法读取账户资料，请重试。');
      if (!await this.persist(revision, token)) return false;
      this.token = token;
      this.publish({ status: 'signedIn', user, pending: false, error: null, notice: null });
      return true;
    } catch (error) {
      if (revision === this.revision) this.publish({ status: 'signedOut', user: null, pending: false,
        error: this.errorMessage(error), notice: null });
      return false;
    }
  };

  signUp = async (email: string, password: string): Promise<boolean> => {
    if (this.snapshot.recovery === 'clear') return false;
    const revision = this.begin();
    this.publish({ status: 'signedOut', user: null, pending: true, error: null, notice: null });
    try {
      await this.api.request('/auth/signup', { method: 'POST', body: { email: email.trim(), password },
        auth: false, signal: this.authRequest?.signal });
      if (revision !== this.revision) return false;
      this.publish({ status: 'signedOut', user: null, pending: false, error: null, notice: '注册成功，请登录。' });
      return true;
    } catch (error) {
      if (revision === this.revision) this.publish({ status: 'signedOut', user: null, pending: false,
        error: this.errorMessage(error), notice: null });
      return false;
    }
  };

  logout = async (notice: string | null = null) => {
    const revision = this.begin();
    this.token = null;
    // Keep auth actions gated until the old credential is removed from disk.
    this.publish({ status: 'restoring', user: null, pending: true, recovery: 'clear', error: null, notice });
    try {
      if (await this.persist(revision, null)) {
        this.publish({ status: 'signedOut', user: null, pending: false, error: null, notice });
      }
    }
    catch {
      if (revision === this.revision) this.publish({ status: 'unavailable', user: null, pending: false,
        recovery: 'clear', error: '无法清除设备上的登录信息，请重试。', notice: null });
    }
  };

  stop = () => { this.begin(); this.token = null; };
}

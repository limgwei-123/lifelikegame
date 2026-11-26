export interface AuthContext { token: string; revision: number }
type Fetcher = typeof fetch;
interface RequestOptions {
  method?: string;
  body?: unknown;
  auth?: boolean;
  context?: AuthContext;
  signal?: AbortSignal;
}

export class ApiError extends Error {
  constructor(public readonly status: number, public readonly code: string, message: string,
    public readonly retryAfter?: number) {
    super(message);
    this.name = 'ApiError';
  }
}

function messageFor(status: number, code: string, authenticated: boolean): string {
  if (status === 401) return authenticated ? '登录已失效，请重新登录。' : '邮箱或密码不正确。';
  if (status === 403) return '暂时无法执行此操作。';
  if (status === 409 && code === 'CONFLICT') return '这个邮箱已经注册，请直接登录。';
  if (status === 422) return '请检查填写的信息后再试。';
  if (status === 429) return '请求过于频繁，请稍后再试。';
  if (status >= 500) return '服务暂时不可用，请稍后重试。';
  return '请求未能完成，请稍后再试。';
}

export class ApiClient {
  constructor(private readonly baseUrl: string,
    private readonly getContext: () => AuthContext | null,
    private readonly unauthorized: (context: AuthContext) => void | Promise<void>,
    private readonly fetcher: Fetcher = fetch) {}

  async request<T = unknown>(path: string, options: RequestOptions = {}): Promise<T> {
    const context = options.auth === false ? null : options.context ?? this.getContext();
    const headers: Record<string, string> = { Accept: 'application/json' };
    if (context) headers.Authorization = `Bearer ${context.token}`;
    if (options.body !== undefined) headers['Content-Type'] = 'application/json';
    const controller = new AbortController();
    const abort = () => controller.abort();
    if (options.signal?.aborted) abort();
    options.signal?.addEventListener('abort', abort, { once: true });
    const timeout = setTimeout(abort, 15000);
    try {
      let response: Response;
      try {
        // Browser fetch cannot be invoked with an ApiClient instance as `this`.
        const fetcher = this.fetcher;
        response = await fetcher(`${this.baseUrl.replace(/\/$/, '')}${path}`, {
          method: options.method ?? 'GET', headers, signal: controller.signal,
          body: options.body === undefined ? undefined : JSON.stringify(options.body),
        });
      } catch {
        throw new ApiError(0, options.signal?.aborted ? 'CANCELLED' : 'NETWORK',
          '暂时无法连接，请检查网络后重试。');
      }
      if (response.status === 204) return null as T;
      let data: unknown;
      try { data = await response.json(); }
      catch {
        if (response.ok) throw new ApiError(502, 'INVALID_RESPONSE', '服务返回异常，请稍后重试。');
        data = null;
      }
      if (!response.ok) {
        // Keep only the domain code, never validation input or a raw error body
        // that may repeat the password submitted to the server.
        const code = data && typeof data === 'object' && 'code' in data && typeof data.code === 'string'
          ? data.code : 'REQUEST_FAILED';
        if (response.status === 401 && context) await this.unauthorized(context);
        const retry = Number(response.headers.get('Retry-After'));
        throw new ApiError(response.status, code, messageFor(response.status, code, !!context),
          Number.isFinite(retry) && retry > 0 ? retry : undefined);
      }
      return data as T;
    } finally {
      clearTimeout(timeout);
      options.signal?.removeEventListener('abort', abort);
    }
  }
}

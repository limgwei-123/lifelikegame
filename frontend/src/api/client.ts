export interface AuthContext { token: string; revision: number }
type Fetcher = typeof fetch;
interface RequestOptions {
  method?: string;
  body?: unknown;
  auth?: boolean;
  context?: AuthContext;
  signal?: AbortSignal;
  timeoutMs?: number;
}

export class ApiError extends Error {
  constructor(public readonly status: number, public readonly code: string, message: string,
    public readonly retryAfter?: number) {
    super(message);
    this.name = 'ApiError';
  }
}

function messageFor(status: number, code: string, authenticated: boolean, path: string, serverMessage?: unknown): string {
  if (status === 401) return authenticated ? '登录已失效，请重新登录。' : '邮箱或密码不正确。';
  if (status === 403) return path === '/auth/change-password' ? '当前密码不正确。' : '暂时无法执行此操作。';
  const aiMessages: Record<string, string> = {
    AI_DAILY_LIMIT_EXCEEDED: '今日 AI 额度已用完，请重置后再试。',
    AI_REQUEST_IN_PROGRESS: '已有 AI 请求正在处理中，请稍候。',
    AI_RATE_LIMITED: 'AI 服务繁忙，请稍后再试。', AI_TIMEOUT: 'AI 生成超时，请稍后重试。',
    AI_CONFIGURATION_ERROR: 'AI 服务尚未配置，请联系管理员。',
    AI_INVALID_OUTPUT: 'AI 返回的计划格式不正确，请重试。', AI_DRAFT_CONSUMED: '这份计划已经确认，请到目标或首页查看。',
  };
  if ((path.startsWith('/ai-planner/') || path === '/workflows/ai/confirm') && Object.hasOwn(aiMessages, code)) return aiMessages[code];
  if (status === 409 && path.startsWith('/workflows/rewards/')) {
    if (serverMessage === 'Not Enough Points') return '积分不足，请先完成任务。';
    if (serverMessage === 'Reward has already been redeemed') return '这个奖励已经兑换过了。';
  }
  if (status === 409) return path === '/auth/signup' ? '这个邮箱已经注册，请直接登录。' : '资料已变更，请刷新后再试。';
  if (status === 404) return '这项资料已不存在，请刷新列表。';
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
    const timeout = setTimeout(abort, options.timeoutMs ?? 15000);
    const connectionError = () => {
      const cancelled = !!options.signal?.aborted, timedOut = controller.signal.aborted && !cancelled;
      return new ApiError(0, cancelled ? 'CANCELLED' : timedOut ? 'TIMEOUT' : 'NETWORK',
        timedOut ? '请求超时，请稍后重试。' : '暂时无法连接，请检查网络后重试。');
    };
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
        throw connectionError();
      }
      if (response.status === 204) return null as T;
      let data: unknown;
      try { data = await response.json(); }
      catch {
        if (controller.signal.aborted) throw connectionError();
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
        const serverMessage = data && typeof data === 'object' && 'message' in data ? data.message : undefined;
        throw new ApiError(response.status, code, messageFor(response.status, code, !!context, path, serverMessage),
          Number.isFinite(retry) && retry > 0 ? retry : undefined);
      }
      return data as T;
    } finally {
      clearTimeout(timeout);
      options.signal?.removeEventListener('abort', abort);
    }
  }
}

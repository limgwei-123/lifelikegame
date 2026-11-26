import { TOKEN_KEY, type TokenStore } from './types';

export const tokenStore: TokenStore = {
  async read() { return typeof window === 'undefined' ? null : window.sessionStorage.getItem(TOKEN_KEY); },
  async write(token) {
    if (typeof window === 'undefined') throw new Error('Browser storage unavailable');
    if (token === null) window.sessionStorage.removeItem(TOKEN_KEY);
    else window.sessionStorage.setItem(TOKEN_KEY, token);
  },
};

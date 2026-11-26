import type { User } from '../api/types';

export interface TokenStore {
  read(): Promise<string | null>;
  write(token: string | null): Promise<void>;
}

export interface SessionSnapshot {
  status: 'restoring' | 'signedOut' | 'signedIn' | 'unavailable';
  user: User | null;
  pending: boolean;
  error: string | null;
  notice: string | null;
  recovery?: 'restore' | 'clear';
}

export const TOKEN_KEY = 'lifelikegame_access_token';

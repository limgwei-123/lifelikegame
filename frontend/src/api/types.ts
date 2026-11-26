export interface User {
  id: string;
  email: string;
  current_value: number;
  display_name: string | null;
  avatar_key: string;
  timezone: string;
}

export function isUser(value: unknown): value is User {
  if (!value || typeof value !== 'object') return false;
  const user = value as Partial<User>;
  return typeof user.id === 'string' && !!user.id && typeof user.email === 'string'
    && typeof user.current_value === 'number' && Number.isFinite(user.current_value)
    && (user.display_name === null || typeof user.display_name === 'string')
    && typeof user.avatar_key === 'string' && typeof user.timezone === 'string';
}

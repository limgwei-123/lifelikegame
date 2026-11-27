export const avatars = [
  { key: 'leaf', name: '冒险者', icon: 'compass' }, { key: 'tree', name: '自然', icon: 'feather' },
  { key: 'sun', name: '阳光', icon: 'sun' }, { key: 'book', name: '阅读', icon: 'book-open' },
] as const;
export type AvatarKey = typeof avatars[number]['key'];
export interface ProfileInput { display_name: string | null; avatar_key: AvatarKey; timezone: string }
export interface ProfileForm { name: string; avatar: string; timezone: string }
export class ProfileValidationError extends Error {
  constructor(public fields: Partial<Record<keyof ProfileForm, string>>) { super(Object.values(fields)[0]); }
}
export function profilePayload(form: ProfileForm): ProfileInput {
  const name = form.name.trim(), timezone = form.timezone.trim();
  const fields: ProfileValidationError['fields'] = {};
  if (Array.from(name).length > 30) fields.name = '昵称最多 30 个字。';
  if (!avatars.some(a => a.key === form.avatar)) fields.avatar = '请选择一个内置头像。';
  try {
    if (!timezone || timezone.length > 64 || !/^[A-Za-z]/.test(timezone)) throw new Error();
    new Intl.DateTimeFormat('en', { timeZone: timezone }).format();
  } catch { fields.timezone = '请选择有效的时区，例如 Asia/Kuala_Lumpur。'; }
  if (Object.keys(fields).length) throw new ProfileValidationError(fields);
  return { display_name: name || null, avatar_key: form.avatar as AvatarKey, timezone };
}
export function passwordErrors(current: string, next: string, confirm: string) {
  const fields: Partial<Record<'current' | 'next' | 'confirm', string>> = {};
  if (!current) fields.current = '请输入当前密码。';
  if (Array.from(next).length < 8 || Array.from(next).length > 128 || !next.trim()) fields.next = '新密码需要 8–128 个字符。';
  if (next !== confirm) fields.confirm = '两次输入的新密码不一致。';
  return fields;
}

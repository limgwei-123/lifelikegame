export type ThemeMode = 'system' | 'light' | 'dark';
export type Accent = 'blue' | 'green' | 'purple' | 'orange';
export interface Preferences { mode: ThemeMode; accent: Accent }
export interface PreferenceStore { read(): Promise<string | null>; write(value: string): Promise<void> }
const defaults: Preferences = { mode: 'system', accent: 'blue' };
function valid(value: unknown): value is Preferences {
  return !!value && typeof value === 'object' && 'mode' in value && 'accent' in value
    && typeof value.mode === 'string' && typeof value.accent === 'string'
    && ['system', 'light', 'dark'].includes(value.mode) && ['blue', 'green', 'purple', 'orange'].includes(value.accent);
}
export function decodePreferences(value: string | null): Preferences {
  try { const parsed: unknown = JSON.parse(value || 'null'); if (valid(parsed)) return { mode: parsed.mode, accent: parsed.accent }; } catch {}
  return { ...defaults };
}
export interface AppearanceState { preferences: Preferences; ready: boolean; saving: boolean; error: string | null }
const initial: AppearanceState = { preferences: defaults, ready: false, saving: false, error: null };
export class AppearanceController {
  private state = initial;
  private revision = 0;
  private listeners = new Set<() => void>();
  constructor(private readonly store: PreferenceStore) {}
  getSnapshot = () => this.state;
  getServerSnapshot = () => initial;
  subscribe = (fn: () => void) => { this.listeners.add(fn); return () => { this.listeners.delete(fn); }; };
  private publish(change: Partial<AppearanceState>) { this.state = { ...this.state, ...change }; this.listeners.forEach(fn => fn()); }
  restore = async () => {
    if (this.state.ready) return;
    const revision = ++this.revision;
    try {
      const preferences = decodePreferences(await this.store.read());
      if (revision === this.revision) this.publish({ preferences, ready: true, error: null });
    } catch { if (revision === this.revision) this.publish({ ready: true, error: '无法读取设备外观设置，已使用默认外观。' }); }
  };
  save = async (preferences: Preferences) => {
    if (!this.state.ready || this.state.saving || !valid(preferences)) return false;
    const revision = ++this.revision;
    const next: Preferences = { mode: preferences.mode, accent: preferences.accent };
    this.publish({ saving: true, error: null });
    try {
      await this.store.write(JSON.stringify(next));
      if (revision !== this.revision) return false;
      this.publish({ preferences: next, saving: false }); return true;
    } catch { if (revision === this.revision) this.publish({ saving: false, error: '无法保存外观设置，请重试。' }); return false; }
  };
}
export const APPEARANCE_KEY = 'lifelikegame_appearance_v1';

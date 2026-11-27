import { APPEARANCE_KEY, type PreferenceStore } from './controller';
export const preferenceStore: PreferenceStore = {
  async read() { return typeof window === 'undefined' ? null : window.localStorage.getItem(APPEARANCE_KEY); },
  async write(value) { if (typeof window === 'undefined') throw new Error('Browser storage unavailable'); window.localStorage.setItem(APPEARANCE_KEY, value); },
};

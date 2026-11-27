import * as SecureStore from 'expo-secure-store';
import { APPEARANCE_KEY, type PreferenceStore } from './controller';
export const preferenceStore: PreferenceStore = {
  read: () => SecureStore.getItemAsync(APPEARANCE_KEY),
  write: value => SecureStore.setItemAsync(APPEARANCE_KEY, value, { keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY }),
};

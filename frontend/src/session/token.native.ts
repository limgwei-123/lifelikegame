import * as SecureStore from 'expo-secure-store';
import { TOKEN_KEY, type TokenStore } from './types';

export const tokenStore: TokenStore = {
  read: () => SecureStore.getItemAsync(TOKEN_KEY),
  write: token => token === null ? SecureStore.deleteItemAsync(TOKEN_KEY)
    : SecureStore.setItemAsync(TOKEN_KEY, token, { keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY }),
};

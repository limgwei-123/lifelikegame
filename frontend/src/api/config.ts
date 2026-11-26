import Constants from 'expo-constants';
import { Platform } from 'react-native';

export function apiBaseUrl(): string {
  const configured = process.env.EXPO_PUBLIC_API_URL?.trim();
  if (configured) return configured.replace(/\/$/, '');
  // Metro's LAN/emulator host is reachable by the device; native localhost
  // would incorrectly refer to the phone itself.
  const metro = Constants.expoConfig?.hostUri;
  const host = Platform.OS === 'web'
    ? (typeof location === 'undefined' ? 'localhost' : location.hostname)
    : metro ? new URL(`http://${metro}`).hostname : '10.0.2.2';
  return `http://${host.includes(':') && !host.startsWith('[') ? `[${host}]` : host}:8000`;
}

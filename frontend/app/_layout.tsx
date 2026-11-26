import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { SessionGate } from '../src/components/SessionGate';
import { SessionProvider, useSession } from '../src/session/SessionProvider';
import { ThemeProvider, useTheme } from '../src/theme/ThemeProvider';

function Routes() {
  const { status } = useSession();
  const { colors, isDark } = useTheme();
  if (status === 'restoring' || status === 'unavailable') return <SessionGate />;
  return <>
    <StatusBar style={isDark ? 'light' : 'dark'} />
    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.background } }}>
      <Stack.Protected guard={status === 'signedIn'}><Stack.Screen name="(tabs)" /></Stack.Protected>
      <Stack.Protected guard={status === 'signedOut'}><Stack.Screen name="(auth)" /></Stack.Protected>
      <Stack.Screen name="+not-found" />
    </Stack>
  </>;
}
export default function RootLayout() {
  return <SafeAreaProvider><ThemeProvider><SessionProvider><Routes /></SessionProvider></ThemeProvider></SafeAreaProvider>;
}

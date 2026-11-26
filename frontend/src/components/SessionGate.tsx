import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { useSession } from '../session/SessionProvider';
import { useTheme } from '../theme/ThemeProvider';
import { Brand, Button, Icon } from './ui';

export function SessionGate() {
  const { status, error, recovery, controller } = useSession();
  const { colors } = useTheme();
  return <View style={[gate.screen, { backgroundColor: colors.background }]}>
    <Brand large />
    {status === 'restoring' ? <View style={gate.status}>
      <ActivityIndicator size="large" color={colors.accent} />
      <Text accessibilityLiveRegion="polite" style={{ color: colors.muted }}>正在处理登录状态…</Text>
    </View> : <View style={gate.status}>
      <Icon name="wifi-off" size={32} color={colors.muted} />
      <Text accessibilityRole="alert" style={[gate.message, { color: colors.text }]}>{error}</Text>
      <Button title="重试" onPress={() => { void controller.restore(); }} />
      {recovery !== 'clear' && <Button title="退出登录" secondary onPress={() => { void controller.logout(); }} />}
    </View>}
  </View>;
}
const gate = StyleSheet.create({
  screen: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 48, padding: 28 },
  status: { width: '100%', maxWidth: 340, alignItems: 'stretch', gap: 20 },
  message: { fontSize: 16, textAlign: 'center', lineHeight: 25 },
});

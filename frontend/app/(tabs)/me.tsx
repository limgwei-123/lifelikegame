import { Text, View } from 'react-native';
import { Page } from '../../src/components/Page';
import { AdventurerAvatar, Button, Card } from '../../src/components/ui';
import { useSession } from '../../src/session/SessionProvider';
import { useTheme } from '../../src/theme/ThemeProvider';

export default function Me() {
  const { user, controller, pending } = useSession();
  const { colors } = useTheme();
  return <Page title="我的">
    <Text accessibilityRole="header" style={{ color: colors.text, fontSize: 28, fontWeight: '800' }}>我的</Text>
    <Card style={{ gap: 24 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 16 }}>
        <AdventurerAvatar />
        <View style={{ flex: 1, gap: 6 }}>
          <Text style={{ color: colors.text, fontSize: 20, fontWeight: '700' }}>{user?.display_name || '冒险者'}</Text>
          <Text selectable style={{ color: colors.muted, fontSize: 13 }}>{user?.email}</Text>
        </View>
      </View>
      <View style={{ height: 1, backgroundColor: colors.border }} />
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 12 }}>
        <Text style={{ color: colors.muted, fontSize: 14 }}>时区</Text>
        <Text style={{ color: colors.text, fontSize: 14 }}>{user?.timezone}</Text>
      </View>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
        <Text style={{ color: colors.muted, fontSize: 14 }}>积分</Text>
        <Text style={{ color: colors.text, fontSize: 14 }}>{user?.current_value}</Text>
      </View>
    </Card>
    <View style={{ maxWidth: 320, width: '100%' }}>
      <Button title="退出登录" icon="log-out" secondary busy={pending} onPress={() => { void controller.logout(); }} />
    </View>
  </Page>;
}

import { router } from 'expo-router';
import { Text, View } from 'react-native';
import { Page } from '../../src/components/Page';
import { Button, Card } from '../../src/components/ui';
import { JourneyArt } from '../../src/components/JourneyArt';
import { useSession } from '../../src/session/SessionProvider';
import { useTheme } from '../../src/theme/ThemeProvider';

export default function Home() {
  const { user } = useSession();
  const { colors } = useTheme();
  return <Page title="首页">
    <View style={{ gap: 9 }}>
      <Text accessibilityRole="header" style={{ color: colors.text, fontSize: 28, fontWeight: '800' }}>你好，{user?.display_name || '冒险者'}</Text>
      <Text style={{ color: colors.muted, fontSize: 14 }}>欢迎回到自己的旅程。</Text>
    </View>
    <Card style={{ alignItems: 'center', paddingVertical: 30 }}>
      <JourneyArt compact />
      <Text style={{ color: colors.text, fontSize: 20, fontWeight: '700', marginVertical: 17 }}>从这里出发</Text>
      <View style={{ width: '100%', maxWidth: 300, gap: 12, marginTop: 8 }}>
        <Button title="看看冒险" icon="compass" onPress={() => router.navigate('/adventure')} />
        <Button title="我的账户" icon="user" secondary onPress={() => router.navigate('/me')} />
      </View>
    </Card>
  </Page>;
}

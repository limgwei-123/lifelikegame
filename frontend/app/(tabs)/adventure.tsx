import { Text } from 'react-native';
import { Page } from '../../src/components/Page';
import { Card } from '../../src/components/ui';
import { JourneyArt } from '../../src/components/JourneyArt';
import { useTheme } from '../../src/theme/ThemeProvider';

export default function Adventure() {
  const { colors } = useTheme();
  return <Page title="冒险">
    <Text accessibilityRole="header" style={{ color: colors.text, fontSize: 28, fontWeight: '800' }}>我的冒险</Text>
    <Card style={{ alignItems: 'center', paddingVertical: 44 }}>
      <JourneyArt />
      <Text style={{ color: colors.text, fontSize: 20, fontWeight: '700', marginTop: 18 }}>旅程即将展开</Text>
    </Card>
  </Page>;
}

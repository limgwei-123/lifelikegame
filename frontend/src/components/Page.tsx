import { ScrollView, Text, View, useWindowDimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { PropsWithChildren, ReactNode } from 'react';
import { Brand, Icon } from './ui';
import { useTheme } from '../theme/ThemeProvider';
import { useSession } from '../session/SessionProvider';
import { useHome } from '../features/home/HomeProvider';

export function Page({ title, children, footer }: PropsWithChildren<{ title: string; footer?: ReactNode }>) {
  const { colors } = useTheme();
  const wide = useWindowDimensions().width >= 900;
  const insets = useSafeAreaInsets();
  const { user } = useSession();
  const { data } = useHome();
  return <View style={{ flex: 1, backgroundColor: colors.background }}>
    <View style={{ paddingTop: Math.max(20, insets.top + 12), paddingBottom: 20, paddingHorizontal: wide ? 40 : 22,
      flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderBottomWidth: 1, borderColor: colors.border }}>
      {wide ? <Text style={{ fontSize: 17, fontWeight: '700', color: colors.text }}>{title}</Text> : <Brand />}
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 16 }}>
      {data && <View accessibilityLabel={`连续行动 ${data.progress.current_streak} 天`} style={{ flexDirection: 'row', alignItems: 'center', gap: 5 }}>
        <Text accessible={false} style={{ fontSize: 17 }}>🔥</Text>
        <Text style={{ color: colors.text, fontSize: 13, fontWeight: '700' }}>{data.progress.current_streak} 天</Text>
      </View>}
      <View accessibilityLabel={`积分 ${user?.current_value ?? 0}`} style={{ flexDirection: 'row', alignItems: 'center', gap: 7 }}>
        <Icon name="award" size={18} color={colors.accent} />
        <Text style={{ color: colors.text, fontSize: 13, fontWeight: '700' }}>{user?.current_value ?? 0}</Text>
      </View>
      </View>
    </View>
    <ScrollView contentContainerStyle={{ padding: wide ? 40 : 22, paddingBottom: 36, flexGrow: 1 }}>
      <View style={{ width: '100%', maxWidth: 960, alignSelf: 'center', gap: 24 }}>{children}</View>
    </ScrollView>
    {footer && <View style={{ paddingHorizontal: wide ? 40 : 22, paddingTop: 12, paddingBottom: 16, borderTopWidth: 1, borderColor: colors.border }}>
      <View style={{ maxWidth: 960, width: '100%', alignSelf: 'center' }}>{footer}</View>
    </View>}
  </View>;
}

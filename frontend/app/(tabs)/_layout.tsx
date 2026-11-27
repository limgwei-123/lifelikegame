import { Tabs } from 'expo-router';
import { Pressable, Text, View, useWindowDimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Brand, Icon, type IconName } from '../../src/components/ui';
import { useSession } from '../../src/session/SessionProvider';
import { useTheme } from '../../src/theme/ThemeProvider';
import { HomeProvider } from '../../src/features/home/HomeProvider';

const destinations: Record<string, { title: string; icon: IconName }> = {
  index: { title: '首页', icon: 'home' }, adventure: { title: '冒险', icon: 'compass' }, me: { title: '我的', icon: 'user' },
};
export default function TabLayout() {
  return <HomeProvider><Navigation /></HomeProvider>;
}
function Navigation() {
  const wide = useWindowDimensions().width >= 900;
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const { user } = useSession();
  return <Tabs screenOptions={{ headerShown: false, tabBarPosition: wide ? 'left' : 'bottom', sceneStyle: { backgroundColor: colors.background } }}
    tabBar={({ state, emitter, navigateToTab }) => <View style={{ backgroundColor: colors.surface, borderColor: colors.border,
      ...(wide ? { width: 228, borderRightWidth: 1, paddingTop: 35, paddingHorizontal: 20, paddingBottom: 25 }
        : { flexDirection: 'row', borderTopWidth: 1, paddingTop: 9, paddingBottom: Math.max(9, insets.bottom), paddingHorizontal: 16 }) }}>
      {wide && <View style={{ paddingHorizontal: 5, marginBottom: 54 }}><Brand /></View>}
      {state.routes.map((route, index) => {
        const item = destinations[route.name];
        if (!item) return null;
        const selected = state.index === index;
        return <Pressable key={route.key} accessibilityRole="tab" accessibilityLabel={item.title} aria-selected={selected} accessibilityState={{ selected }}
          onPress={() => {
            const event = emitter.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
            if (!selected && !event.defaultPrevented) navigateToTab(route.key);
          }} onLongPress={() => emitter.emit({ type: 'tabLongPress', target: route.key })}
          style={({ pressed }) => ({ flex: wide ? undefined : 1, flexDirection: wide ? 'row' : 'column', alignItems: 'center',
            justifyContent: wide ? 'flex-start' : 'center', gap: wide ? 14 : 4, paddingVertical: wide ? 17 : 7,
            paddingHorizontal: wide ? 18 : 0, marginBottom: wide ? 10 : 0, borderRadius: 15,
            backgroundColor: selected ? colors.accentSoft : 'transparent', opacity: pressed ? 0.7 : 1 })}>
          <Icon name={item.icon} size={22} color={selected ? colors.accent : colors.muted} />
          <Text style={{ color: selected ? colors.accent : colors.muted, fontSize: wide ? 15 : 11, fontWeight: selected ? '700' : '500' }}>{item.title}</Text>
        </Pressable>;
      })}
      {wide && <View style={{ flex: 1, justifyContent: 'flex-end', paddingHorizontal: 8, gap: 6 }}>
        <Text numberOfLines={1} style={{ color: colors.text, fontWeight: '700', fontSize: 13 }}>{user?.display_name || '冒险者'}</Text>
        <Text numberOfLines={1} style={{ color: colors.muted, fontSize: 11 }}>{user?.email}</Text>
      </View>}
    </View>}>
    <Tabs.Screen name="index" options={{ title: '首页' }} />
    <Tabs.Screen name="adventure" options={{ title: '冒险' }} />
    <Tabs.Screen name="me" options={{ title: '我的' }} />
  </Tabs>;
}

import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { Page } from '../../components/Page';
import { Button, Card, Icon, Message, type IconName } from '../../components/ui';
import { useSession } from '../../session/SessionProvider';
import { useTheme } from '../../theme/ThemeProvider';
import { useHome } from '../home/HomeProvider';
import { AppearanceSheet } from './AppearanceSheet';
import { PasswordSheet } from './PasswordSheet';
import { ProfileSheet } from './ProfileSheet';
import { UserAvatar } from './UserAvatar';

export function AccountScreen() {
  const { user, controller: session, pending } = useSession();
  const { colors, preferences } = useTheme();
  const { busy, error, notice, controller } = useHome();
  const [panel, setPanel] = useState<'profile' | 'password' | 'appearance' | null>(null);
  useFocusEffect(useCallback(() => { void controller.refresh(); }, [controller]));
  const open = (value: typeof panel) => { controller.clearMessages(); setPanel(value); };
  const row = (title: string, subtitle: string, icon: IconName, value: Exclude<typeof panel, null>, last = false) =>
    <Pressable accessibilityRole="button" accessibilityLabel={title} onPress={() => open(value)} disabled={busy}
      style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', gap: 13, padding: 20,
        borderBottomWidth: last ? 0 : 1, borderColor: colors.border, opacity: pressed || busy ? 0.6 : 1 })}>
      <View style={{ padding: 11, borderRadius: 13, backgroundColor: colors.accentSoft }}><Icon name={icon} color={colors.accent} size={20} /></View>
      <View style={{ flex: 1, gap: 6 }}><Text style={{ color: colors.text, fontSize: 15, fontWeight: '700' }}>{title}</Text>
        <Text style={{ color: colors.muted, fontSize: 12 }}>{subtitle}</Text></View>
      <Icon name="chevron-right" color={colors.muted} size={18} />
    </Pressable>;
  const modeName = { light: '浅色', dark: '深色', system: '跟随系统' }[preferences.mode];
  return <Page title="我的">
    <Text accessibilityRole="header" style={{ color: colors.text, fontSize: 28, fontWeight: '800' }}>我的</Text>
    <Card style={{ gap: 20 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 18 }}>
        <UserAvatar avatarKey={user?.avatar_key} size={72} />
        <View style={{ flex: 1, gap: 8 }}>
          <Text testID="profile-name" style={{ color: colors.text, fontSize: 22, fontWeight: '800' }}>{user?.display_name || '冒险者'}</Text>
          <Text selectable style={{ color: colors.muted, fontSize: 13 }}>{user?.email}</Text>
        </View>
      </View>
      <View style={{ height: 1, backgroundColor: colors.border }} />
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 7 }}><Icon name="globe" size={14} color={colors.muted} />
        <Text testID="profile-timezone" style={{ color: colors.muted, fontSize: 12 }}>{user?.timezone}</Text>
      </View>
    </Card>
    <Message text={error} /><Message text={notice} success />
    <Card style={{ padding: 0, overflow: 'hidden' }}>
      {row('个人资料', '昵称、头像与时区', 'user', 'profile')}
      {row('修改密码', '账户安全', 'shield', 'password')}
      {row('外观设置', modeName, 'sliders', 'appearance', true)}
    </Card>
    <View style={{ maxWidth: 340, width: '100%' }}><Button title="退出登录" icon="log-out" secondary busy={pending} disabled={busy}
      onPress={() => { void session.logout(); }} /></View>
    {panel === 'profile' && <ProfileSheet onClose={() => setPanel(null)} />}
    {panel === 'password' && <PasswordSheet onClose={() => setPanel(null)} />}
    {panel === 'appearance' && <AppearanceSheet onClose={() => setPanel(null)} />}
  </Page>;
}

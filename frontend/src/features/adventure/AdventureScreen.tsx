import { useFocusEffect } from 'expo-router';
import { useCallback } from 'react';
import { ActivityIndicator, Pressable, Text, View, useWindowDimensions } from 'react-native';
import { Page } from '../../components/Page';
import { Button, Card, Icon, Message } from '../../components/ui';
import { useTheme } from '../../theme/ThemeProvider';
import { useHome } from '../home/HomeProvider';
import { BossArt } from './art';
import { BossCard } from './BossCard';

export function AdventureScreen() {
  const { colors } = useTheme();
  const wide = useWindowDimensions().width >= 1100;
  const { data, feedback, loading, busy, error, controller } = useHome();
  useFocusEffect(useCallback(() => { void controller.refresh(); }, [controller]));
  const progress = data?.progress;
  return <Page title="冒险">
    <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
      <Text accessibilityRole="header" style={{ color: colors.text, fontSize: 28, fontWeight: '800' }}>我的冒险</Text>
      <Pressable accessibilityRole="button" accessibilityLabel="刷新冒险" disabled={loading || busy} onPress={() => { void controller.refresh(); }} style={{ padding: 12 }}>
        {loading ? <ActivityIndicator size="small" color={colors.muted} /> : <Icon name="refresh-cw" size={18} color={colors.muted} />}
      </Pressable>
    </View>
    <Message text={error} />
    {!progress ? <View style={{ paddingVertical: 50 }}>{loading ? <ActivityIndicator color={colors.accent} /> : <Button title="重试" secondary onPress={() => { void controller.refresh(); }} />}</View>
      : <>
        <View style={{ flexDirection: wide ? 'row' : 'column', gap: 24, alignItems: 'stretch' }}>
          <View style={{ flex: wide ? 1 : undefined, gap: 20 }}>
            <BossCard progress={progress} feedback={feedback} />
            <Card style={{ flexDirection: 'row', padding: 20, justifyContent: 'space-around' }}>
              <View style={{ alignItems: 'center', gap: 8 }}><Text style={{ color: colors.muted, fontSize: 12 }}>累计行动</Text><Text style={{ color: colors.text, fontWeight: '800', fontSize: 22 }}>{progress.total_completed}</Text></View>
              <View style={{ width: 1, backgroundColor: colors.border }} />
              <View style={{ alignItems: 'center', gap: 8 }}><Text style={{ color: colors.muted, fontSize: 12 }}>已击败</Text><Text style={{ color: colors.accent, fontWeight: '800', fontSize: 22 }}>{progress.defeated_bosses}</Text></View>
            </Card>
          </View>
          <View style={{ flex: wide ? 1.25 : undefined, gap: 17 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
              <Text style={{ color: colors.text, fontSize: 17, fontWeight: '800' }}>本轮旅程</Text>
              <Text style={{ color: colors.muted, fontSize: 12 }}>第 {progress.boss.round} 轮</Text>
            </View>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12 }}>
              {progress.bosses.map((boss, index) => <View key={boss.id} testID={`boss-roster-${boss.id}`}
                style={{ width: '47.5%', flexGrow: 1, borderWidth: boss.status === 'current' ? 1.5 : 1, borderColor: boss.status === 'current' ? colors.accent : colors.border,
                  borderRadius: 20, padding: 15, alignItems: 'center', gap: 9, backgroundColor: boss.status === 'current' ? colors.accentSoft : colors.surface }}>
                <View style={{ alignSelf: 'stretch', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text style={{ color: colors.muted, fontSize: 10 }}>0{index + 1}</Text>
                  {boss.status === 'defeated' && <Icon name="check-circle" color={colors.success} size={15} />}
                  {boss.status === 'current' && <Icon name="flag" color={colors.accent} size={15} />}
                </View>
                <View style={{ opacity: boss.status === 'upcoming' ? 0.65 : 1 }}><BossArt id={boss.id} size={78} name={boss.name} /></View>
                <Text style={{ color: colors.text, fontSize: 13, fontWeight: '700' }}>{boss.name}</Text>
                <Text style={{ color: boss.status === 'defeated' ? colors.success : boss.status === 'current' ? colors.accent : colors.muted, fontSize: 11 }}>
                  {{ defeated: '已通过', current: '挑战中', upcoming: '待挑战' }[boss.status]} · {boss.max_hp} HP</Text>
              </View>)}
            </View>
          </View>
        </View>
      </>}
  </Page>;
}

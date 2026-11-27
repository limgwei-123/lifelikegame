import { useEffect, useRef } from 'react';
import { Animated, Pressable, Text, View } from 'react-native';
import type { Progress } from '../../api/tasks';
import { Card, Icon } from '../../components/ui';
import { useTheme } from '../../theme/ThemeProvider';
import { BossArt } from './art';
import { hpFraction, type AdventureFeedback } from './model';
import { useReducedMotion } from './useReducedMotion';

export function BossCard({ progress, compact = false, feedback, onPress }:
  { progress: Progress; compact?: boolean; feedback?: AdventureFeedback | null; onPress?: () => void }) {
  const { colors } = useTheme();
  const { boss } = progress;
  const reduced = useReducedMotion();
  const shake = useRef(new Animated.Value(0)).current;
  // A cached card or navigation mount must not replay a consumed completion.
  const consumed = useRef(feedback?.instanceId);
  useEffect(() => {
    if (!feedback || consumed.current === feedback.instanceId) return;
    consumed.current = feedback.instanceId;
    if (reduced || feedback.kind !== 'hit' || feedback.bossId !== boss.id || feedback.round !== boss.round) return;
    const animation = Animated.sequence([-5, 5, -3, 3, 0].map(value => Animated.timing(shake, { toValue: value, duration: 55, useNativeDriver: true })));
    animation.start(); return () => { animation.stop(); shake.setValue(0); };
  }, [feedback, boss.id, boss.round, reduced, shake]);
  const hp = <View style={{ width: '100%', gap: compact ? 8 : 12 }}>
    <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 5 }}><Icon name="heart" size={13} color={colors.success} /><Text style={{ color: colors.muted, fontSize: 11 }}>HP</Text></View>
      <Text testID={compact ? 'home-boss-hp' : 'adventure-boss-hp'} style={{ color: colors.text, fontWeight: '700', fontSize: compact ? 12 : 15 }}>{boss.hp} / {boss.max_hp}</Text>
    </View>
    <View role="progressbar" accessibilityLabel={`${boss.name}剩余血量`} aria-valuemin={0} aria-valuemax={boss.max_hp} aria-valuenow={boss.hp}
      accessibilityValue={{ min: 0, max: boss.max_hp, now: boss.hp }} style={{ height: compact ? 7 : 10, borderRadius: 10, overflow: 'hidden', backgroundColor: colors.mutedSurface }}>
      <View style={{ height: '100%', width: `${hpFraction(boss) * 100}%`, borderRadius: 10, backgroundColor: colors.success }} />
    </View>
  </View>;
  const body = <View testID={compact ? 'home-boss' : 'current-boss'}><Card style={{ padding: compact ? 18 : 28, gap: compact ? 14 : 24,
    ...(compact ? { flexDirection: 'row', alignItems: 'center' } : { alignItems: 'center' }) }}>
    <Animated.View style={{ transform: [{ translateX: shake }], ...(compact ? {} : { backgroundColor: colors.accentSoft, borderRadius: 120, width: 220, height: 220, alignItems: 'center', justifyContent: 'center' }) }}>
      <BossArt id={boss.id} size={compact ? 76 : 186} />
    </Animated.View>
    <View style={{ flex: compact ? 1 : undefined, width: compact ? undefined : '100%', gap: compact ? 10 : 16, alignItems: compact ? 'stretch' : 'center' }}>
      <View style={{ gap: 6, alignItems: compact ? 'flex-start' : 'center' }}>
        <Text style={{ color: colors.muted, fontSize: 11 }}>第 {boss.round} 轮 · 第 {boss.position} 站</Text>
        <Text style={{ color: colors.text, fontSize: compact ? 16 : 23, fontWeight: '800' }}>{boss.name}</Text>
      </View>
      {hp}
    </View>
    {compact && <Icon name="chevron-right" color={colors.muted} size={18} />}
  </Card></View>;
  return onPress ? <Pressable accessibilityRole="button" accessibilityLabel="查看冒险" onPress={onPress} style={({ pressed }) => ({ opacity: pressed ? 0.8 : 1 })}>{body}</Pressable> : body;
}

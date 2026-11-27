import { useEffect, useRef } from 'react';
import { Animated, Pressable, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Icon } from '../../components/ui';
import { useTheme } from '../../theme/ThemeProvider';
import type { AdventureFeedback } from './model';
import { useReducedMotion } from './useReducedMotion';

export function CompletionToast({ feedback, onDismiss }: { feedback: AdventureFeedback; onDismiss: (id: number) => void }) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const reduced = useReducedMotion();
  const offset = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(feedback.instanceId), 3200);
    return () => clearTimeout(timer);
  }, [feedback.instanceId, onDismiss]);
  useEffect(() => {
    offset.setValue(0);
    if (reduced) return;
    const animation = Animated.sequence([
      Animated.timing(offset, { toValue: -5, duration: 110, useNativeDriver: true }),
      Animated.spring(offset, { toValue: 0, friction: 6, useNativeDriver: true }),
    ]);
    animation.start(); return () => { animation.stop(); offset.setValue(0); };
  }, [feedback.instanceId, reduced, offset]);
  return <View pointerEvents="box-none" style={{ position: 'absolute', left: 16, right: 16, top: insets.top + 16, alignItems: 'center' }}>
    <Animated.View testID="adventure-feedback" role="status" accessibilityLiveRegion="polite"
      style={{ width: '100%', maxWidth: 440, padding: 16, borderRadius: 19, backgroundColor: colors.surface, borderWidth: 1,
        borderColor: colors.accent, flexDirection: 'row', alignItems: 'center', gap: 12, transform: [{ translateY: offset }],
        boxShadow: '0 8px 28px rgba(20,35,60,0.15)' }}>
      <View style={{ backgroundColor: colors.accentSoft, padding: 10, borderRadius: 13 }}><Icon name={feedback.kind === 'defeat' ? 'award' : 'zap'} color={colors.accent} /></View>
      <View style={{ flex: 1, gap: 5 }}>
        <Text style={{ color: colors.text, fontSize: 14, fontWeight: '800' }}>{feedback.kind === 'defeat' ? `击败了${feedback.defeatedName}` : '命中！-1 HP'}</Text>
        {feedback.kind === 'defeat' && <Text style={{ color: colors.muted, fontSize: 12 }}>下一站：{feedback.nextName}</Text>}
      </View>
      <Pressable accessibilityRole="button" accessibilityLabel="收起冒险反馈" onPress={() => onDismiss(feedback.instanceId)} style={{ padding: 10 }}><Icon name="x" size={17} color={colors.muted} /></Pressable>
    </Animated.View>
  </View>;
}

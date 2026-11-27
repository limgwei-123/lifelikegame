import { KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, Text, View, useWindowDimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { PropsWithChildren } from 'react';
import { useTheme } from '../theme/ThemeProvider';
import { Icon } from './ui';

export function Sheet({ title, onClose, busy = false, children }: PropsWithChildren<{ title: string; onClose: () => void; busy?: boolean }>) {
  const { colors } = useTheme();
  const wide = useWindowDimensions().width >= 700;
  const insets = useSafeAreaInsets();
  const close = () => { if (!busy) onClose(); };
  return <Modal transparent visible animationType="fade" onRequestClose={close}>
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={{ flex: 1, justifyContent: wide ? 'center' : 'flex-end', alignItems: 'center', padding: wide ? 24 : 0, paddingTop: insets.top + 12 }}>
      <Pressable accessibilityLabel="关闭弹窗背景" onPress={close} disabled={busy}
        style={{ position: 'absolute', top: 0, bottom: 0, left: 0, right: 0, backgroundColor: 'rgba(15,25,45,0.4)' }} />
      <View role="dialog" aria-modal accessibilityLabel={title} accessibilityViewIsModal style={{ width: '100%', maxWidth: 540, maxHeight: '95%', backgroundColor: colors.surface,
        borderRadius: 26, borderBottomLeftRadius: wide ? 26 : 0, borderBottomRightRadius: wide ? 26 : 0, overflow: 'hidden' }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingLeft: 24, paddingRight: 12,
          paddingVertical: 12, borderBottomWidth: 1, borderColor: colors.border }}>
          <Text accessibilityRole="header" style={{ fontSize: 19, fontWeight: '800', color: colors.text }}>{title}</Text>
          <Pressable accessibilityRole="button" accessibilityLabel="关闭" disabled={busy} onPress={close}
            style={{ padding: 14, opacity: busy ? 0.4 : 1 }}><Icon name="x" size={20} color={colors.muted} /></Pressable>
        </View>
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ padding: 24, paddingBottom: Math.max(24, insets.bottom + 16), gap: 20 }}>
          {children}
        </ScrollView>
      </View>
    </KeyboardAvoidingView>
  </Modal>;
}

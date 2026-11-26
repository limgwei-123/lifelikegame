import Feather from '@expo/vector-icons/Feather';
import { useState, type ComponentProps, type ComponentRef, type PropsWithChildren, type Ref } from 'react';
import { ActivityIndicator, Image, Pressable, StyleSheet, Text, TextInput, View, type TextInputProps, type ViewStyle } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';

export type IconName = ComponentProps<typeof Feather>['name'];
export function Icon({ name, size = 20, color }: { name: IconName; size?: number; color?: string }) {
  const { colors } = useTheme();
  return <Feather name={name} size={size} color={color ?? colors.text} accessible={false} />;
}

export function AdventurerAvatar({ size = 60 }: { size?: number }) {
  const { colors } = useTheme();
  return <View style={{ width: size, height: size, borderRadius: size * 0.3, backgroundColor: colors.accentSoft,
    alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
    <Image source={require('../../assets/brand/adventurer.png')} accessible={false} resizeMode="contain"
      style={{ width: size * 0.9, height: size * 0.9 }} />
  </View>;
}

export function Brand({ large = false }: { large?: boolean }) {
  const { colors } = useTheme();
  return <View style={styles.brand}>
    <AdventurerAvatar size={large ? 43 : 32} />
    <Text style={{ color: colors.text, fontWeight: '800', fontSize: large ? 22 : 16, letterSpacing: -0.5 }}>Lifelikegame</Text>
  </View>;
}

export function Button({ title, onPress, busy = false, secondary = false, icon, disabled = false, testID }:
  { title: string; onPress: () => void; busy?: boolean; secondary?: boolean; icon?: IconName; disabled?: boolean; testID?: string }) {
  const { colors } = useTheme();
  const unavailable = disabled || busy;
  return <Pressable accessibilityRole="button" accessibilityLabel={title}
    accessibilityState={{ disabled: unavailable, busy }} disabled={unavailable} onPress={onPress} testID={testID}
    style={({ pressed }) => [styles.button, { backgroundColor: secondary ? colors.mutedSurface : colors.accent,
      opacity: unavailable ? 0.65 : pressed ? 0.8 : 1 }]}>
    {busy ? <ActivityIndicator color={secondary ? colors.text : colors.accentText} />
      : icon ? <Icon name={icon} color={secondary ? colors.text : colors.accentText} size={18} /> : null}
    <Text style={[styles.buttonText, { color: secondary ? colors.text : colors.accentText }]}>{title}</Text>
  </Pressable>;
}

export function Field({ label, icon, secret = false, inputRef, ...props }:
  TextInputProps & { label: string; icon: IconName; secret?: boolean; inputRef?: Ref<ComponentRef<typeof TextInput>> }) {
  const { colors } = useTheme();
  const [focused, setFocused] = useState(false);
  const [visible, setVisible] = useState(false);
  return <View style={{ gap: 9 }}>
    <Text style={{ color: colors.text, fontSize: 13, fontWeight: '600' }}>{label}</Text>
    <View style={[styles.field, { backgroundColor: colors.surface, borderColor: focused ? colors.accent : colors.border }]}>
      <Icon name={icon} size={18} color={colors.muted} />
      <TextInput {...props} ref={inputRef} accessibilityLabel={label} placeholderTextColor={colors.muted}
        secureTextEntry={secret && !visible} onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}
        style={[styles.input, { color: colors.text }]} />
      {secret && <Pressable accessibilityRole="button" accessibilityLabel={visible ? '隐藏密码' : '显示密码'}
        onPress={() => setVisible(value => !value)} hitSlop={10} style={styles.eye}>
        <Icon name={visible ? 'eye-off' : 'eye'} color={colors.muted} size={18} />
      </Pressable>}
    </View>
  </View>;
}

export function Card({ children, style }: PropsWithChildren<{ style?: ViewStyle }>) {
  const { colors } = useTheme();
  return <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }, style]}>{children}</View>;
}

export function Message({ text, success = false }: { text: string | null; success?: boolean }) {
  const { colors } = useTheme();
  if (!text) return null;
  return <View style={[styles.message, { backgroundColor: success ? colors.successSoft : colors.dangerSoft }]}>
    <Text accessibilityRole="alert" accessibilityLiveRegion="polite"
      style={{ color: success ? colors.success : colors.danger, fontSize: 13, lineHeight: 21 }}>{text}</Text>
  </View>;
}

export const styles = StyleSheet.create({
  brand: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  button: { minHeight: 50, paddingHorizontal: 20, borderRadius: 14, alignItems: 'center', justifyContent: 'center', flexDirection: 'row', gap: 9 },
  buttonText: { fontSize: 15, fontWeight: '700' },
  field: { borderWidth: 1, borderRadius: 13, paddingLeft: 15, flexDirection: 'row', alignItems: 'center', minHeight: 53, gap: 10 },
  input: { flex: 1, fontSize: 15, minHeight: 51, paddingVertical: 12, paddingRight: 12, outlineWidth: 0 },
  eye: { minWidth: 44, minHeight: 48, alignItems: 'center', justifyContent: 'center' },
  card: { borderRadius: 24, borderWidth: 1, padding: 24 },
  message: { padding: 12, borderRadius: 12 },
});

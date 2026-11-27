import { Pressable, Text } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';

export function Chip({ label, selected = false, onPress, disabled = false }: { label: string; selected?: boolean; onPress: () => void; disabled?: boolean }) {
  const { colors } = useTheme();
  return <Pressable accessibilityRole="button" accessibilityLabel={label} aria-pressed={selected} accessibilityState={{ selected, disabled }}
    onPress={onPress} disabled={disabled} style={({ pressed }) => ({ paddingHorizontal: 15, minHeight: 43, paddingVertical: 11,
      justifyContent: 'center', borderRadius: 12, borderWidth: 1, borderColor: selected ? colors.accent : colors.border,
      backgroundColor: selected ? colors.accentSoft : colors.surface, opacity: disabled ? 0.5 : pressed ? 0.7 : 1 })}>
    <Text style={{ color: selected ? colors.accent : colors.text, fontSize: 13, fontWeight: selected ? '700' : '500' }}>{label}</Text>
  </Pressable>;
}

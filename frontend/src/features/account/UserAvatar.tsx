import { View } from 'react-native';
import { AdventurerAvatar, Icon, type IconName } from '../../components/ui';
import { useTheme } from '../../theme/ThemeProvider';

export function UserAvatar({ avatarKey = 'leaf', size = 64 }: { avatarKey?: string; size?: number }) {
  const { colors } = useTheme();
  const badge: IconName | null = { tree: 'feather', sun: 'sun', book: 'book-open' }[avatarKey] as IconName | undefined ?? null;
  const badgeSize = Math.max(20, size * 0.33);
  return <View testID={`avatar-${avatarKey}`} style={{ width: size, height: size }}>
    <AdventurerAvatar size={size} />
    {badge && <View style={{ position: 'absolute', right: -3, bottom: -3, width: badgeSize, height: badgeSize,
      borderRadius: badgeSize / 2, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.accent,
      borderWidth: 2, borderColor: colors.surface }}><Icon name={badge} size={Math.max(11, badgeSize * 0.5)} color={colors.accentText} /></View>}
  </View>;
}

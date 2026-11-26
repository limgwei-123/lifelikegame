import { Image, StyleSheet, Text, View } from 'react-native';
import { Icon } from './ui';
import { useTheme } from '../theme/ThemeProvider';

export function JourneyArt({ compact = false }: { compact?: boolean }) {
  const { colors } = useTheme();
  return <View accessible={false} style={[art.scene, { height: compact ? 160 : 240 }]}>
    <View style={[art.orbit, { borderColor: colors.border, width: compact ? 150 : 222, height: compact ? 150 : 222 }]} />
    <View style={[art.orbit, { borderColor: colors.border, width: compact ? 104 : 158, height: compact ? 104 : 158 }]} />
    <View style={[art.tile, { backgroundColor: colors.accentSoft, borderColor: colors.surface,
      transform: [{ rotate: '-12deg' }], width: compact ? 78 : 114, height: compact ? 78 : 114 }]}>
      <Image source={require('../../assets/brand/adventurer.png')} resizeMode="contain" accessible={false}
        style={{ width: '90%', height: '90%' }} />
    </View>
    <View style={[art.badge, { top: compact ? 15 : 29, right: compact ? '18%' : '12%', backgroundColor: colors.successSoft }]}>
      <Icon name="check" color={colors.success} size={22} />
    </View>
    <View style={[art.dot, { bottom: 29, left: '16%', backgroundColor: colors.accent }]} />
    <Text style={[art.star, { top: 18, left: '17%', color: colors.accent }]}>✦</Text>
    <Text style={[art.star, { bottom: 14, right: '17%', color: colors.muted }]}>✧</Text>
  </View>;
}
const art = StyleSheet.create({
  scene: { width: '100%', alignItems: 'center', justifyContent: 'center' },
  orbit: { position: 'absolute', borderRadius: 200, borderWidth: 1 },
  tile: { borderRadius: 28, borderWidth: 5, alignItems: 'center', justifyContent: 'center' },
  badge: { position: 'absolute', width: 43, height: 43, borderRadius: 14, alignItems: 'center', justifyContent: 'center', transform: [{ rotate: '10deg' }] },
  dot: { position: 'absolute', width: 9, height: 9, borderRadius: 9, opacity: 0.5 },
  star: { position: 'absolute', fontSize: 28 },
});

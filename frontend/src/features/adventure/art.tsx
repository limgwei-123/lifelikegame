import { Image, View } from 'react-native';
import { Icon } from '../../components/ui';

const art = {
  slime: require('../../../assets/bosses/slime.png'), cloud: require('../../../assets/bosses/cloud.png'),
  mushroom: require('../../../assets/bosses/mushroom.png'), pillow: require('../../../assets/bosses/pillow.png'),
  stone: require('../../../assets/bosses/stone.png'), dragon: require('../../../assets/bosses/dragon.png'),
};
export function BossArt({ id, size = 160, name }: { id: string; size?: number; name?: string }) {
  const source = Object.hasOwn(art, id) ? art[id as keyof typeof art] : null;
  return source ? <Image source={source} accessibilityLabel={name} accessible={!!name} resizeMode="contain" style={{ width: size, height: size }} />
    : <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}><Icon name="compass" size={size / 2} /></View>;
}

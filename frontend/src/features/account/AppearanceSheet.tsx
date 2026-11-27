import { Pressable, Text, View } from 'react-native';
import { Chip } from '../../components/Chip';
import { Sheet } from '../../components/Sheet';
import { Button, Icon, Message } from '../../components/ui';
import { useTheme } from '../../theme/ThemeProvider';
import type { Accent, ThemeMode } from '../../theme/controller';

export function AppearanceSheet({ onClose }: { onClose: () => void }) {
  const { colors, preferences, saving, error, setPreferences } = useTheme();
  const modes: { mode: ThemeMode; label: string }[] = [{ mode: 'light', label: '浅色' }, { mode: 'dark', label: '深色' }, { mode: 'system', label: '跟随系统' }];
  const accents: { key: Accent; name: string; color: string }[] = [
    { key: 'blue', name: '蓝色', color: '#365dce' }, { key: 'green', name: '绿色', color: '#247a60' },
    { key: 'purple', name: '紫色', color: '#7550ba' }, { key: 'orange', name: '橙色', color: '#b45a20' },
  ];
  return <Sheet title="外观设置" onClose={onClose} busy={saving}>
    <View style={{ gap: 13 }}><Text style={{ color: colors.text, fontWeight: '600', fontSize: 14 }}>显示模式</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10 }}>{modes.map(item => <Chip key={item.mode} label={item.label}
        selected={preferences.mode === item.mode} disabled={saving} onPress={() => { void setPreferences({ ...preferences, mode: item.mode }); }} />)}</View>
    </View>
    <View style={{ gap: 13 }}><Text style={{ color: colors.text, fontWeight: '600', fontSize: 14 }}>主题色</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 18 }}>{accents.map(accent => <Pressable key={accent.key} accessibilityRole="button"
        accessibilityLabel={accent.name} aria-pressed={preferences.accent === accent.key} disabled={saving}
        onPress={() => { void setPreferences({ ...preferences, accent: accent.key }); }} style={{ alignItems: 'center', paddingVertical: 5, gap: 9 }}>
        <View style={{ width: 52, height: 52, borderRadius: 18, alignItems: 'center', justifyContent: 'center',
          borderWidth: preferences.accent === accent.key ? 2 : 1, borderColor: preferences.accent === accent.key ? colors.text : colors.border }}>
          <View style={{ width: 40, height: 40, borderRadius: 12, backgroundColor: accent.color, alignItems: 'center', justifyContent: 'center' }}>
            {preferences.accent === accent.key && <Icon name="check" color="#ffffff" size={20} />}
          </View>
        </View>
        <Text style={{ color: colors.muted, fontSize: 12 }}>{accent.name}</Text>
      </Pressable>)}</View>
    </View>
    <Text accessibilityLiveRegion="polite" style={{ color: colors.muted, fontSize: 12 }}>{saving ? '正在保存…' : '自动保存到此设备。'}</Text>
    <Message text={error} />
    <Button title="恢复默认外观" secondary disabled={saving} onPress={() => { void setPreferences({ mode: 'system', accent: 'blue' }); }} />
  </Sheet>;
}

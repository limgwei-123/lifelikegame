import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { Button, Icon } from '../../components/ui';
import { Sheet } from '../../components/Sheet';
import { useTheme } from '../../theme/ThemeProvider';
import { dateLabel, monthGrid, shiftMonth, weekNames } from './dates';

export function Calendar({ value, onSelect, onClose, today, marked = [], onMonthChange, allowClear = false }:
  { value: string; today: string; onSelect: (date: string) => void; onClose: () => void;
    marked?: string[]; onMonthChange?: (date: string) => void; allowClear?: boolean }) {
  const { colors } = useTheme();
  const [month, setMonth] = useState(value);
  const move = (delta: number) => { const next = shiftMonth(month, delta); setMonth(next); onMonthChange?.(next); };
  return <Sheet title="选择日期" onClose={onClose}>
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
      <Pressable accessibilityRole="button" accessibilityLabel="上个月" onPress={() => move(-1)} style={{ padding: 12 }}><Icon name="chevron-left" /></Pressable>
      <Text style={{ color: colors.text, fontSize: 17, fontWeight: '700' }}>{Number(month.slice(0, 4))}年 {Number(month.slice(5, 7))}月</Text>
      <Pressable accessibilityRole="button" accessibilityLabel="下个月" onPress={() => move(1)} style={{ padding: 12 }}><Icon name="chevron-right" /></Pressable>
    </View>
    <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
      {weekNames.map(name => <View key={name} style={{ width: '14.2857%', alignItems: 'center', paddingBottom: 12 }}>
        <Text style={{ color: colors.muted, fontSize: 12 }}>{name}</Text>
      </View>)}
      {monthGrid(month).map((date, index) => <View key={date ?? `blank-${index}`} style={{ width: '14.2857%', padding: 2 }}>
        {date ? <Pressable accessibilityRole="button" accessibilityLabel={date} aria-pressed={date === value} accessibilityState={{ selected: date === value }}
          onPress={() => onSelect(date)} style={{ height: 46, alignItems: 'center', justifyContent: 'center', borderRadius: 12,
            backgroundColor: date === value ? colors.accent : date === today ? colors.accentSoft : 'transparent', gap: 3 }}>
          <Text style={{ fontSize: 14, fontWeight: date === value || date === today ? '700' : '400', color: date === value ? colors.accentText : colors.text }}>{Number(date.slice(8))}</Text>
          <View style={{ width: 4, height: 4, borderRadius: 4, backgroundColor: marked.includes(date) ? date === value ? colors.accentText : colors.accent : 'transparent' }} />
        </Pressable> : <View style={{ height: 46 }} />}
      </View>)}
    </View>
    <Button title="回到今天" secondary onPress={() => onSelect(today)} />
    {allowClear && <Button title="不设结束日期" secondary onPress={() => onSelect('')} />}
  </Sheet>;
}

export function DateField({ label, value, base, today, onChange, optional = false, disabled = false }:
  { label: string; value: string; base: string; today: string; onChange: (date: string) => void; optional?: boolean; disabled?: boolean }) {
  const { colors } = useTheme();
  const [open, setOpen] = useState(false);
  return <View style={{ gap: 9 }}>
    <Text style={{ color: colors.text, fontSize: 13, fontWeight: '600' }}>{label}</Text>
    <Pressable accessibilityRole="button" accessibilityLabel={label} disabled={disabled} onPress={() => setOpen(true)}
      style={{ minHeight: 51, borderWidth: 1, borderColor: colors.border, borderRadius: 13, paddingHorizontal: 15, gap: 10,
        flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
      <Text style={{ color: value ? colors.text : colors.muted, fontSize: 14 }}>{value || '不设结束日期'}</Text>
      <Icon name="calendar" color={colors.muted} size={18} />
    </Pressable>
    {open && <Calendar value={value || base} today={today} onClose={() => setOpen(false)} allowClear={optional}
      onSelect={date => { onChange(date); setOpen(false); }} />}
  </View>;
}

import { Text, View } from 'react-native';
import type { DraftPlan, DraftTask } from '../../api/ai';
import type { ScoringScheme } from '../../api/tasks';
import { Chip } from '../../components/Chip';
import { Button, Card, Field, Icon, Message } from '../../components/ui';
import { useTheme } from '../../theme/ThemeProvider';
import { weekNames } from '../tasks/dates';

export function PlanEditor({ plan, onChange, schemes, disabled }: { plan: DraftPlan; onChange: (plan: DraftPlan) => void; schemes: ScoringScheme[]; disabled: boolean }) {
  const { colors } = useTheme();
  const update = (index: number, change: Partial<DraftTask>) => onChange({ ...plan, tasks: plan.tasks.map((task, i) => i === index ? { ...task, ...change } : task) });
  return <View style={{ gap: 18 }}>
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 9 }}><Icon name="map" color={colors.accent} size={20} />
      <Text accessibilityRole="header" style={{ color: colors.text, fontSize: 21, fontWeight: '800' }}>你的行动计划</Text>
      <Text style={{ color: colors.muted, marginLeft: 'auto', fontSize: 12 }}>{plan.tasks.length} / 3</Text></View>
    <Card><Field label="目标名称" icon="flag" value={plan.goal_title} onChangeText={goal_title => onChange({ ...plan, goal_title })} editable={!disabled} maxLength={510} /></Card>
    {plan.tasks.map((task, index) => <Card key={index} style={{ gap: 18 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}><Text style={{ color: colors.accent, fontSize: 13, fontWeight: '800' }}>任务 {index + 1}</Text>
        <View style={{ flex: 1 }} /><Button title={`移除任务 ${index + 1}`} icon="trash-2" secondary disabled={disabled || plan.tasks.length <= 1}
          onPress={() => onChange({ ...plan, tasks: plan.tasks.filter((_, i) => i !== index) })} /></View>
      <Field label={`任务 ${index + 1} 名称`} icon="edit-3" value={task.title} onChangeText={title => update(index, { title })} editable={!disabled} maxLength={510} />
      <Field label={`任务 ${index + 1} 备注`} icon="align-left" value={task.description || ''} onChangeText={description => update(index, { description })} editable={!disabled} multiline />
      <View style={{ gap: 10 }}><Text style={{ color: colors.muted, fontSize: 12 }}>重复</Text><View style={{ flexDirection: 'row', gap: 8 }}>
        <Chip label="每天" accessibilityLabel={`任务 ${index + 1} 每天`} selected={task.schedule_type === 'daily'} disabled={disabled} onPress={() => update(index, { schedule_type: 'daily', schedule_value_json: {} })} />
        <Chip label="每周" accessibilityLabel={`任务 ${index + 1} 每周`} selected={task.schedule_type === 'weekly'} disabled={disabled} onPress={() => update(index, { schedule_type: 'weekly', schedule_value_json: { days: [0, 2, 4] } })} />
      </View></View>
      {task.schedule_type === 'weekly' && <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 7 }}>{weekNames.map((name, day) => {
        const days = task.schedule_value_json.days || [];
        return <Chip key={day} label={`周${name}`} accessibilityLabel={`任务 ${index + 1} 周${name}`} selected={days.includes(day)} disabled={disabled}
          onPress={() => update(index, { schedule_value_json: { days: days.includes(day) ? days.filter(d => d !== day) : [...days, day] } })} />;
      })}</View>}
      <View style={{ gap: 10 }}><Text style={{ color: colors.muted, fontSize: 12 }}>评分方案</Text><View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 7 }}>
        <Chip label="系统默认" accessibilityLabel={`任务 ${index + 1} 系统默认`} selected={task.scoring_scheme_id === null} disabled={disabled} onPress={() => update(index, { scoring_scheme_id: null })} />
        {schemes.map(scheme => <Chip key={scheme.id} label={scheme.title} accessibilityLabel={`任务 ${index + 1} ${scheme.title}`} selected={task.scoring_scheme_id === scheme.id} disabled={disabled}
          onPress={() => update(index, { scoring_scheme_id: scheme.id })} />)}
      </View></View>
      <Message text={task.scoring_scheme_id !== null && !schemes.some(s => s.id === task.scoring_scheme_id) ? '评分方案已移除，请重新选择。' : null} />
    </Card>)}
    {plan.tasks.length < 3 && <Button title="添加一个任务" icon="plus" secondary disabled={disabled} onPress={() => onChange({ ...plan,
      tasks: [...plan.tasks, { title: '', description: null, scoring_scheme_id: null, schedule_type: 'daily', schedule_value_json: {} }] })} />}
  </View>;
}

import { Pressable, Text, View } from 'react-native';
import type { Task, TaskInstance, TaskSchedule } from '../../api/tasks';
import { Icon } from '../../components/ui';
import { useTheme } from '../../theme/ThemeProvider';
import { completionLevels } from './model';
import { dateLabel } from './dates';

export function TaskCard({ item, task, schedule, goalTitle, today, locked, onComplete, onMenu }:
  { item: TaskInstance; task: Task; schedule?: TaskSchedule; goalTitle?: string; today: string; locked: boolean;
    onComplete: () => void; onMenu: () => void }) {
  const { colors } = useTheme();
  const finished = item.status === 'done', future = item.date_instance > today;
  const levels = completionLevels(task, item);
  return <View testID={`task-instance-${item.id}`} style={{ backgroundColor: colors.surface, borderRadius: 19,
    borderWidth: 1, borderColor: colors.border, padding: 16, flexDirection: 'row', alignItems: 'center', gap: 10 }}>
    <Pressable accessibilityRole="checkbox" accessibilityLabel={`完成 ${task.title}`} aria-checked={finished} accessibilityState={{ checked: finished, disabled: locked || finished || future }}
      disabled={locked || finished || future} onPress={onComplete} style={{ width: 44, height: 44, justifyContent: 'center', alignItems: 'center' }}>
      <View style={{ width: 25, height: 25, borderRadius: 9, borderWidth: finished ? 0 : 1.5, borderColor: future ? colors.border : colors.accent,
        backgroundColor: finished ? colors.successSoft : 'transparent', alignItems: 'center', justifyContent: 'center' }}>
        {finished && <Icon name="check" size={16} color={colors.success} />}
      </View>
    </Pressable>
    <View style={{ flex: 1, gap: 7 }}>
      <Text style={{ color: finished ? colors.muted : colors.text, fontSize: 15, fontWeight: '600', textDecorationLine: finished ? 'line-through' : 'none' }}>{task.title}</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
        <Text style={{ color: colors.muted, fontSize: 11 }}>{goalTitle || (task.goal_id ? '目标任务' : '普通待办')}</Text>
        {schedule && schedule.schedule_type !== 'once' && <Text style={{ color: colors.muted, fontSize: 11 }}>
          {{ daily: '每天', weekly: '每周', monthly: '每月' }[schedule.schedule_type]}</Text>}
        {task.goal_id !== null && <Text style={{ color: colors.accent, fontSize: 11 }}>
          {finished ? `+${item.score_awarded} 分` : levels.length === 1 ? `+${levels[0][1]} 分` : `${levels.length} 档评分`}</Text>}
        {!finished && item.date_instance < today && <Text style={{ color: colors.danger, fontSize: 11 }}>逾期 · {dateLabel(item.date_instance)}</Text>}
        {future && !finished && <Text style={{ color: colors.muted, fontSize: 11 }}>尚未到期</Text>}
      </View>
      {finished && item.completion_level && <Text style={{ color: colors.muted, fontSize: 11 }}>{item.completion_level}</Text>}
    </View>
    <Pressable accessibilityRole="button" accessibilityLabel={`管理 ${task.title}`} onPress={onMenu} disabled={locked}
      style={{ padding: 10 }}><Icon name="more-horizontal" size={20} color={colors.muted} /></Pressable>
  </View>;
}

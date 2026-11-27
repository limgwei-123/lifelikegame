import { useState } from 'react';
import { Text, View } from 'react-native';
import type { Task, TaskSchedule } from '../../api/tasks';
import { Chip } from '../../components/Chip';
import { Sheet } from '../../components/Sheet';
import { Button, Field, Message } from '../../components/ui';
import { useTheme } from '../../theme/ThemeProvider';
import { useHome } from '../home/HomeProvider';
import { DateField } from './Calendar';
import { weekday, weekNames } from './dates';
import { buildTaskPayload, type TaskFormValue } from './model';

export function TaskForm({ task, schedule, scheduleOnly = false, onClose }:
  { task?: Task; schedule?: TaskSchedule; scheduleOnly?: boolean; onClose: () => void }) {
  const { colors } = useTheme();
  const { data, selectedDate, busy, error, controller } = useHome();
  const today = data!.progress.today;
  const [form, setForm] = useState<TaskFormValue>({ title: task?.title ?? '', description: task?.description ?? '',
    goalId: task?.goal_id ?? null, schemeId: task?.scoring_scheme_id ?? null, kind: schedule?.schedule_type ?? 'once',
    start: schedule?.start_date || selectedDate || today, end: schedule?.end_date || '',
    days: schedule?.schedule_value_json.days ?? [weekday(selectedDate || today)],
    monthDay: schedule?.schedule_value_json.day ?? Number((selectedDate || today).slice(8)) });
  const [validation, setValidation] = useState<string | null>(null);
  const set = <K extends keyof TaskFormValue>(key: K, value: TaskFormValue[K]) => setForm(old => ({ ...old, [key]: value }));
  const creating = !task;
  const submit = async () => {
    if (busy) return;
    setValidation(null);
    try {
      if (!form.title.trim() || form.title.trim().length > 255) throw new Error('任务名称需要 1–255 个字符。');
      const result = creating ? await controller.create(buildTaskPayload(form))
        : scheduleOnly && schedule ? await controller.updateSchedule(schedule.id, buildTaskPayload(form).schedule)
          : await controller.editTask(task.id, form.title, form.description);
      if (result) onClose();
    } catch (failure) { setValidation(failure instanceof Error ? failure.message : '请检查输入。'); }
  };
  const label = (title: string) => <Text style={{ color: colors.text, fontSize: 13, fontWeight: '600' }}>{title}</Text>;
  return <Sheet title={creating ? '添加任务' : scheduleOnly ? '重复设置' : '编辑任务'} onClose={onClose} busy={busy}>
    {!scheduleOnly && <>
      <Field label="任务名称" icon="edit-3" placeholder="想完成什么？" value={form.title} onChangeText={value => set('title', value)} maxLength={255} editable={!busy} />
      <Field label="备注（选填）" icon="align-left" placeholder="补充一点细节" value={form.description} onChangeText={value => set('description', value)} multiline editable={!busy} />
    </>}
    {creating && <>
      <View style={{ gap: 10 }}>{label('目标（选填）')}
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
          <Chip label="普通待办" selected={form.goalId === null} onPress={() => set('goalId', null)} disabled={busy} />
          {data!.goals.map(goal => <Chip key={goal.id} label={goal.title} selected={form.goalId === goal.id} onPress={() => set('goalId', goal.id)} disabled={busy} />)}
        </View>
      </View>
      {form.goalId !== null && <View style={{ gap: 10 }}>{label('评分方案')}
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
          <Chip label="系统默认" selected={form.schemeId === null} onPress={() => set('schemeId', null)} disabled={busy} />
          {data!.schemes.map(scheme => <Chip key={scheme.id} label={scheme.title} selected={form.schemeId === scheme.id} onPress={() => set('schemeId', scheme.id)} disabled={busy} />)}
        </View>
      </View>}
    </>}
    {(creating || scheduleOnly) && <>
      <View style={{ gap: 10 }}>{label('重复')}
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
          {(['once', 'daily', 'weekly', 'monthly'] as const).filter(kind => creating || kind !== 'once').map(kind =>
            <Chip key={kind} label={{ once: '不重复', daily: '每天', weekly: '每周', monthly: '每月' }[kind]}
              selected={form.kind === kind} onPress={() => set('kind', kind)} disabled={busy} />)}
        </View>
      </View>
      {form.kind === 'weekly' && <View style={{ gap: 10 }}>{label('重复日')}
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 7 }}>
          {weekNames.map((name, index) => <Chip key={name} label={`周${name}`} selected={form.days.includes(index)} disabled={busy}
            onPress={() => set('days', form.days.includes(index) ? form.days.filter(d => d !== index) : [...form.days, index])} />)}
        </View>
      </View>}
      {form.kind === 'monthly' && <>
        <Field label="每月几号" icon="calendar" value={String(form.monthDay || '')} onChangeText={value => set('monthDay', Number(value))} keyboardType="number-pad" maxLength={2} editable={!busy} />
        {form.monthDay > 28 && <Text style={{ color: colors.muted, fontSize: 12, lineHeight: 19 }}>没有这一天的月份会跳过。</Text>}
      </>}
      <DateField label={form.kind === 'once' ? '任务日期' : '开始日期'} value={form.start} base={today} today={today} onChange={date => set('start', date)} disabled={busy} />
      {form.kind !== 'once' && <DateField label="结束日期（选填）" value={form.end} base={form.start} today={today} onChange={date => set('end', date)} optional disabled={busy} />}
      {scheduleOnly && <Text style={{ color: colors.muted, fontSize: 12, lineHeight: 20 }}>已生成的当前任务保留原日期；重复规则用于后续安排。</Text>}
    </>}
    <Message text={validation || error} />
    <Button title={creating ? '添加任务' : '保存修改'} onPress={() => { void submit(); }} busy={busy} icon={creating ? 'plus' : 'check'} />
  </Sheet>;
}

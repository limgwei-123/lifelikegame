import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';
import type { Task, TaskInstance, TaskSchedule } from '../../api/tasks';
import { Page } from '../../components/Page';
import { Sheet } from '../../components/Sheet';
import { Button, Card, Icon, Message } from '../../components/ui';
import { useTheme } from '../../theme/ThemeProvider';
import { Calendar } from '../tasks/Calendar';
import { TaskForm } from '../tasks/TaskForm';
import { TaskCard } from '../tasks/TaskCard';
import { addDays, weekday, weekNames } from '../tasks/dates';
import { completionLevels, visibleInstances } from '../tasks/model';
import { useHome } from './HomeProvider';

type Editor = { task?: Task; schedule?: TaskSchedule; scheduleOnly?: boolean };
export function HomeScreen() {
  const { colors } = useTheme();
  const { data, selectedDate, loading, busy, error, notice, controller } = useHome();
  const [editor, setEditor] = useState<Editor | null>(null);
  const [menu, setMenu] = useState<Task | null>(null);
  const [deleting, setDeleting] = useState<Task | null>(null);
  const [scoring, setScoring] = useState<TaskInstance | null>(null);
  const [calendar, setCalendar] = useState(false);
  const [paused, setPaused] = useState(false);
  useFocusEffect(useCallback(() => { void controller.refresh(true); }, [controller]));
  const locked = busy || loading;
  const select = (date: string) => { if (!busy) void controller.selectDate(date); };
  const selected = selectedDate || data?.progress.today;
  const dateReady = data?.date === selected;
  const rows = data && selected && dateReady ? visibleInstances(selected, data.progress.today, data.day, data.pending, data.tasks) : [];
  const todo = rows.filter(i => i.status === 'todo'), done = rows.filter(i => i.status === 'done');
  const scoringTask = data?.tasks.find(t => t.id === scoring?.task_id);
  const complete = (task: Task, item: TaskInstance) => {
    const levels = completionLevels(task, item);
    if (levels.length > 1) setScoring(item);
    else void controller.complete(item, task.goal_id !== null ? levels[0]?.[0] : undefined);
  };
  const action = (label: string, icon: 'edit-3' | 'repeat' | 'pause' | 'play' | 'trash-2', fn: () => void) =>
    <Pressable accessibilityRole="button" accessibilityLabel={label} disabled={locked} onPress={fn}
      style={{ flexDirection: 'row', alignItems: 'center', gap: 13, paddingVertical: 14, opacity: locked ? 0.5 : 1 }}>
      <Icon name={icon} color={icon === 'trash-2' ? colors.danger : colors.text} />
      <Text style={{ color: icon === 'trash-2' ? colors.danger : colors.text, fontSize: 15 }}>{label}</Text>
    </Pressable>;
  const taskRow = (item: TaskInstance) => {
    const task = data!.tasks.find(t => t.id === item.task_id);
    if (!task) return <View key={item.id} testID={`task-instance-${item.id}`}><Card style={{ flexDirection: 'row', alignItems: 'center', gap: 13, padding: 20 }}>
      <Icon name="check" color={colors.success} size={20} />
      <View style={{ flex: 1, gap: 6 }}><Text style={{ color: colors.muted, fontSize: 14 }}>已删除的任务</Text>
        {!!item.completion_level && <Text style={{ color: colors.muted, fontSize: 11 }}>{item.completion_level}</Text>}</View>
      {item.score_awarded !== 0 && <Text style={{ color: colors.accent, fontSize: 12 }}>+{item.score_awarded} 分</Text>}
    </Card></View>;
    return <TaskCard key={item.id} item={item} task={task} schedule={data!.schedules.find(s => s.id === item.task_schedule_id)}
      goalTitle={data!.goals.find(g => g.id === task.goal_id)?.title} today={data!.progress.today} locked={locked}
      onComplete={() => complete(task, item)} onMenu={() => setMenu(task)} />;
  };
  return <Page title="首页" footer={<Button title="添加任务" icon="plus" disabled={locked || !data} onPress={() => setEditor({})} />}>
    {selected && data && <>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <Pressable accessibilityRole="button" accessibilityLabel="打开月历" disabled={busy} onPress={() => setCalendar(true)}
          style={{ flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 8 }}>
          <Text accessibilityRole="header" style={{ color: colors.text, fontSize: 23, fontWeight: '800' }}>{Number(selected.slice(0, 4))}年 {Number(selected.slice(5, 7))}月</Text>
          <Icon name="chevron-down" size={18} color={colors.muted} />
        </Pressable>
        <Pressable accessibilityRole="button" accessibilityLabel="今天" disabled={busy} onPress={() => select(data.progress.today)}
          style={{ paddingVertical: 10, paddingHorizontal: 14, borderRadius: 11, backgroundColor: colors.accentSoft }}>
          <Text style={{ color: colors.accent, fontSize: 13, fontWeight: '700' }}>今天</Text>
        </Pressable>
      </View>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3 }}>
        <Pressable accessibilityRole="button" accessibilityLabel="上一周" disabled={busy} onPress={() => select(addDays(selected, -7))} style={{ paddingVertical: 16, paddingRight: 5 }}><Icon name="chevron-left" size={16} color={colors.muted} /></Pressable>
        {weekNames.map((name, index) => {
          const day = addDays(selected, index - weekday(selected)), active = day === selected;
          const marked = data.month.some(i => i.date_instance === day && (i.status === 'done' || data.tasks.some(t => t.id === i.task_id && t.is_active)));
          return <Pressable key={day} accessibilityRole="button" accessibilityLabel={day} aria-pressed={active} accessibilityState={{ selected: active }} disabled={busy}
            onPress={() => select(day)} style={{ flex: 1, alignItems: 'center', paddingVertical: 12, gap: 10, borderRadius: 15, backgroundColor: active ? colors.accent : 'transparent' }}>
            <Text style={{ fontSize: 11, color: active ? colors.accentText : colors.muted }}>{name}</Text>
            <Text style={{ fontSize: 18, fontWeight: '700', color: active ? colors.accentText : day === data.progress.today ? colors.accent : colors.text }}>{Number(day.slice(8))}</Text>
            <View style={{ width: 4, height: 4, borderRadius: 4, backgroundColor: marked ? active ? colors.accentText : colors.accent : 'transparent' }} />
          </Pressable>;
        })}
        <Pressable accessibilityRole="button" accessibilityLabel="下一周" disabled={busy} onPress={() => select(addDays(selected, 7))} style={{ paddingVertical: 16, paddingLeft: 5 }}><Icon name="chevron-right" size={16} color={colors.muted} /></Pressable>
      </View>
      <Card style={{ flexDirection: 'row', justifyContent: 'space-between', padding: 20 }}>
        <View style={{ gap: 9 }}>
          <Text style={{ color: colors.muted, fontSize: 12 }}>{selected === data.progress.today ? '今日已完成' : '当天任务已完成'}</Text>
          <Text testID="completion-count" style={{ color: colors.text, fontSize: 26, fontWeight: '800' }}>{selected === data.progress.today ? data.progress.completed_today : dateReady ? done.length : '—'}<Text style={{ fontSize: 12, fontWeight: '400', color: colors.muted }}> 件</Text></Text>
        </View>
        <View style={{ width: 1, backgroundColor: colors.border }} />
        <View style={{ gap: 9, minWidth: 85 }}>
          <Text style={{ color: colors.muted, fontSize: 12 }}>待完成</Text>
          <Text style={{ color: colors.accent, fontSize: 26, fontWeight: '800' }}>{loading || !dateReady ? '—' : todo.length}<Text style={{ fontSize: 12, fontWeight: '400', color: colors.muted }}> 件</Text></Text>
        </View>
      </Card>
    </>}
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
      <Text style={{ fontSize: 18, color: colors.text, fontWeight: '800' }}>任务清单</Text>
      <Pressable accessibilityRole="button" accessibilityLabel="刷新任务" disabled={locked} onPress={() => { void controller.refresh(true); }} style={{ padding: 12 }}><Icon name="refresh-cw" size={17} color={colors.muted} /></Pressable>
    </View>
    <Message text={error} /><Message text={notice} success />
    {loading ? <View style={{ paddingVertical: 35 }}><ActivityIndicator color={colors.accent} accessibilityLabel="加载任务" /></View>
      : <View style={{ gap: 12 }}>
        {todo.map(taskRow)}
        {!rows.length && data && dateReady && <Card style={{ paddingVertical: 35, alignItems: 'center', gap: 15 }}>
          <Icon name="check-square" size={30} color={colors.muted} /><Text style={{ color: colors.muted, fontSize: 14 }}>这一天没有任务</Text>
        </Card>}
        {!!done.length && <View style={{ gap: 12, marginTop: todo.length ? 10 : 0 }}>
          <Text style={{ color: colors.muted, fontSize: 12 }}>已完成 · {done.length}</Text>{done.map(taskRow)}
        </View>}
      </View>}
    {!loading && (!data || !dateReady) && <Button title="重试" secondary onPress={() => { void controller.refresh(true); }} />}
    {!!data?.tasks.some(t => !t.is_active) && <View style={{ gap: 10 }}>
      <Pressable accessibilityRole="button" accessibilityLabel="已暂停的任务" onPress={() => setPaused(!paused)} style={{ paddingVertical: 12, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <Icon name={paused ? 'chevron-down' : 'chevron-right'} size={15} color={colors.muted} />
        <Text style={{ color: colors.muted, fontSize: 12 }}>已暂停 · {data.tasks.filter(t => !t.is_active).length}</Text>
      </Pressable>
      {paused && data.tasks.filter(t => !t.is_active).map(task => <Pressable key={task.id} accessibilityRole="button" accessibilityLabel={`管理 ${task.title}`} onPress={() => setMenu(task)}
        style={{ backgroundColor: colors.mutedSurface, borderRadius: 14, padding: 17, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Text style={{ color: colors.muted, fontSize: 14 }}>{task.title}</Text><Icon name="more-horizontal" color={colors.muted} />
      </Pressable>)}
    </View>}
    {editor && data && <TaskForm {...editor} onClose={() => setEditor(null)} />}
    {calendar && selected && data && <Calendar value={selected} today={data.progress.today} marked={data.month.map(i => i.date_instance)} onMonthChange={select}
      onClose={() => setCalendar(false)} onSelect={day => { select(day); setCalendar(false); }} />}
    {menu && data && <Sheet title={menu.title} onClose={() => setMenu(null)} busy={busy}>
      {action('编辑任务', 'edit-3', () => { setEditor({ task: menu }); setMenu(null); })}
      {data.schedules.filter(s => s.task_id === menu.id && s.schedule_type !== 'once').map((schedule, index) => <View key={schedule.id}>
        {action(`重复设置${index ? ` ${index + 1}` : ''}`, 'repeat', () => { setEditor({ task: menu, schedule, scheduleOnly: true }); setMenu(null); })}
      </View>)}
      {action(menu.is_active ? '暂停任务' : '恢复任务', menu.is_active ? 'pause' : 'play', () => { const task = menu; setMenu(null); void controller.toggleTask(task); })}
      {action('删除任务', 'trash-2', () => { setDeleting(menu); setMenu(null); })}
    </Sheet>}
    {deleting && <Sheet title="删除任务" busy={busy} onClose={() => setDeleting(null)}>
      <Text style={{ color: colors.text, lineHeight: 24 }}>删除「{deleting.title}」？之后不会继续生成任务；已有积分与行动记录会保留。</Text>
      <Message text={error} /><Button title="确认删除" busy={busy} onPress={() => { void controller.deleteTask(deleting.id).then(ok => { if (ok) setDeleting(null); }); }} />
      <Button title="保留任务" secondary disabled={busy} onPress={() => setDeleting(null)} />
    </Sheet>}
    {scoring && scoringTask && <Sheet title="完成情况" busy={busy} onClose={() => setScoring(null)}>
      <Text style={{ color: colors.text, fontSize: 15 }}>{scoringTask.title}</Text>
      {completionLevels(scoringTask, scoring).map(([level, score]) =>
        <Button key={level} title={`${level} · +${score} 分`} secondary disabled={busy} onPress={() => { void controller.complete(scoring, level).then(ok => { if (ok) setScoring(null); }); }} />)}
      <Message text={error} />
    </Sheet>}
  </Page>;
}

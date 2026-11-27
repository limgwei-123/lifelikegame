import { router, useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';
import type { EditableItem, ManagementKind, Reward } from '../../api/management';
import { Chip } from '../../components/Chip';
import { Page } from '../../components/Page';
import { Sheet } from '../../components/Sheet';
import { Button, Card, Icon, Message, type IconName } from '../../components/ui';
import { useSession } from '../../session/SessionProvider';
import { useTheme } from '../../theme/ThemeProvider';
import { useHome } from '../home/HomeProvider';
import { ManagementEditor } from './ManagementEditor';
import { redemptionTitle } from './model';

const titles = { goals: '目标', scoring: '评分方案', rewards: '奖励', points: '积分记录' };
export function ManagementScreen({ kind }: { kind: ManagementKind }) {
  const { colors } = useTheme();
  const { user } = useSession();
  const { data, management, busy, loading, error, notice, controller } = useHome();
  const [editor, setEditor] = useState<EditableItem | null>(null), [deleting, setDeleting] = useState<EditableItem | null>(null);
  const [redeeming, setRedeeming] = useState<Reward | null>(null);
  const [history, setHistory] = useState(false);
  useEffect(() => { if (loading) setRedeeming(null); }, [loading]);
  useFocusEffect(useCallback(() => { controller.clearMessages(); void controller.refreshManagement(); }, [controller]));
  const locked = busy || loading;
  const ready = !!data && (kind === 'goals' || kind === 'scoring' || !!management);
  const open = (item: EditableItem) => { controller.clearMessages(); setEditor(item); };
  const remove = async () => {
    if (!deleting?.value || locked) return;
    const ok = deleting.kind === 'goals' ? await controller.deleteGoal(deleting.value.id)
      : deleting.kind === 'scoring' ? await controller.deleteScheme(deleting.value.id) : await controller.deleteReward(deleting.value.id);
    if (ok) setDeleting(null);
  };
  const controls = (item: EditableItem) => <View style={{ flexDirection: 'row', gap: 5 }}>
    <Pressable accessibilityRole="button" accessibilityLabel={`编辑 ${item.value!.title}`} disabled={locked} onPress={() => open(item)} style={{ padding: 11 }}><Icon name="edit-3" color={colors.muted} size={16} /></Pressable>
    <Pressable accessibilityRole="button" accessibilityLabel={`删除 ${item.value!.title}`} disabled={locked} onPress={() => { controller.clearMessages(); setDeleting(item); }} style={{ padding: 11 }}><Icon name="trash-2" color={colors.muted} size={16} /></Pressable>
  </View>;
  const heading = (title: string, item: EditableItem, subtitle?: string) => <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
    <View style={{ flex: 1, gap: 7 }}><Text style={{ color: colors.text, fontSize: 16, fontWeight: '700' }}>{title}</Text>
      {!!subtitle && <Text style={{ color: colors.muted, fontSize: 12 }}>{subtitle}</Text>}</View>{controls(item)}
  </View>;
  const empty = (icon: IconName, text: string) => <Card style={{ alignItems: 'center', gap: 15, paddingVertical: 36 }}>
    <Icon name={icon} size={30} color={colors.muted} /><Text style={{ color: colors.muted, fontSize: 14 }}>{text}</Text>
  </Card>;
  return <Page title={titles[kind]} footer={kind !== 'points' ? <Button title={`添加${titles[kind]}`} icon="plus" disabled={locked || !ready} onPress={() => open({ kind })} /> : undefined}>
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
      <Pressable accessibilityRole="button" accessibilityLabel="返回我的" onPress={() => router.dismissTo('/me')} style={{ paddingVertical: 12, paddingRight: 10 }}><Icon name="arrow-left" size={21} /></Pressable>
      <Text accessibilityRole="header" style={{ flex: 1, color: colors.text, fontSize: 25, fontWeight: '800' }}>{titles[kind]}</Text>
      <Pressable accessibilityRole="button" accessibilityLabel="刷新管理列表" disabled={locked} onPress={() => { void controller.refreshManagement(); }} style={{ padding: 12 }}><Icon name="refresh-cw" color={colors.muted} size={18} /></Pressable>
    </View>
    {(kind === 'rewards' || kind === 'points') && <Card style={{ gap: 9 }}>
      <Text style={{ color: colors.muted, fontSize: 12 }}>可用积分</Text>
      <Text testID="management-balance" style={{ color: colors.text, fontSize: 30, fontWeight: '800' }}>{user?.current_value ?? 0}</Text>
    </Card>}
    <Message text={error} /><Message text={notice} success />
    {kind === 'rewards' && <View style={{ flexDirection: 'row', gap: 9 }}>
      <Chip label="我的奖励" selected={!history} onPress={() => setHistory(false)} disabled={busy} />
      <Chip label="兑换记录" selected={history} onPress={() => setHistory(true)} disabled={busy} />
    </View>}
    {loading ? <View style={{ paddingVertical: 35 }}><ActivityIndicator color={colors.accent} /></View> : !ready
      ? <Button title="重试" secondary onPress={() => { void controller.refreshManagement(); }} /> : <View style={{ gap: 14 }}>
        {kind === 'goals' && (!data!.goals.length ? empty('flag', '还没有目标') : data!.goals.map(goal => <Card key={goal.id} style={{ gap: 15 }}>
          {heading(goal.title, { kind: 'goals', value: goal })}
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 7 }}><Icon name="calendar" size={13} color={colors.muted} /><Text style={{ color: colors.muted, fontSize: 11 }}>{goal.start_date}{goal.target_date ? ` → ${goal.target_date}` : ''}</Text></View>
          {(goal.current_value || goal.target_value) && <Text style={{ color: colors.accent, fontSize: 13 }}>{goal.current_value || '—'} → {goal.target_value || '—'}</Text>}
        </Card>))}
        {kind === 'scoring' && (!data!.schemes.length ? empty('layers', '还没有自定义评分方案') : data!.schemes.map(scheme => <Card key={scheme.id} style={{ gap: 15 }}>
          {heading(scheme.title, { kind: 'scoring', value: scheme })}
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>{Object.entries(scheme.levels_json || {}).map(([name, value]) =>
            <View key={name} style={{ paddingHorizontal: 11, paddingVertical: 8, backgroundColor: colors.accentSoft, borderRadius: 10 }}>
              <Text style={{ color: colors.accent, fontSize: 12 }}>{name} · {value >= 0 ? '+' : ''}{value} 分</Text>
            </View>)}</View>
        </Card>))}
        {kind === 'rewards' && !history && (!management!.rewards.length ? empty('gift', '还没有奖励') : management!.rewards.map(reward => <Card key={reward.id} style={{ gap: 15 }}>
          {heading(reward.title, { kind: 'rewards', value: reward }, `${reward.cost_points} 分`)}
          {!!reward.description && <Text style={{ color: colors.muted, lineHeight: 21, fontSize: 13 }}>{reward.description}</Text>}
          {reward.status === 'redeemed' ? <Text style={{ color: colors.success, fontSize: 13 }}>已兑换</Text>
            : <Button title={(user?.current_value ?? 0) < reward.cost_points ? `积分不足 · 需要 ${reward.cost_points} 分` : `兑换 ${reward.title}`} secondary
              disabled={locked || (user?.current_value ?? 0) < reward.cost_points} onPress={() => { controller.clearMessages(); setRedeeming(reward); }} />}
        </Card>))}
        {kind === 'rewards' && history && (!management!.redemptions.length ? empty('gift', '还没有兑换记录') : [...management!.redemptions].sort((a, b) => b.id - a.id).map(record => <Card key={record.id} style={{ gap: 11 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}><Icon name="check-circle" color={colors.success} size={20} />
            <Text style={{ flex: 1, color: colors.text, fontSize: 15, fontWeight: '700' }}>{redemptionTitle(record)}</Text><Text style={{ color: colors.muted, fontSize: 14 }}>{record.cost_points} 分</Text></View>
          <Text style={{ color: colors.muted, fontSize: 11 }}>{management!.ledger.find(entry => entry.source_type === 'redemption' && entry.source_id === record.id)?.event_at || record.created_at.split('T')[0]}</Text>
        </Card>))}
        {kind === 'points' && (!management!.ledger.length ? empty('list', '还没有积分记录') : [...management!.ledger].sort((a, b) => b.id - a.id).map(entry => {
          const record = management!.redemptions.find(r => entry.source_type === 'redemption' && r.id === entry.source_id);
          const task = data!.tasks.find(t => entry.source_type === 'task_instance' && data!.month.some(i => i.id === entry.source_id && i.task_id === t.id));
          return <Card key={entry.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 14, padding: 20 }}>
            <View style={{ padding: 11, borderRadius: 13, backgroundColor: entry.delta < 0 ? colors.mutedSurface : colors.successSoft }}><Icon name={entry.delta < 0 ? 'arrow-up-right' : 'arrow-down-left'} color={entry.delta < 0 ? colors.muted : colors.success} size={20} /></View>
            <View style={{ flex: 1, gap: 7 }}><Text style={{ color: colors.text, fontSize: 14, fontWeight: '600' }}>{record ? `兑换：${redemptionTitle(record)}` : entry.source_type === 'task_instance' ? task?.title || '任务完成' : entry.delta < 0 ? '积分支出' : '积分收入'}</Text>
              <Text style={{ color: colors.muted, fontSize: 11 }}>{entry.event_at}</Text></View>
            <Text style={{ color: entry.delta < 0 ? colors.text : colors.success, fontSize: 18, fontWeight: '800' }}>{entry.delta >= 0 ? '+' : ''}{entry.delta}</Text>
          </Card>;
        }))}
      </View>}
    {editor && data && <ManagementEditor item={editor} onClose={() => setEditor(null)} />}
    {deleting?.value && <Sheet title={`删除${titles[deleting.kind]}`} busy={busy} onClose={() => setDeleting(null)}>
      <Text style={{ color: colors.text, lineHeight: 25 }}>确定删除「{deleting.value.title}」？</Text>
      <Text style={{ color: colors.muted, fontSize: 13, lineHeight: 21 }}>{deleting.kind === 'goals' ? '该目标的任务会从清单中移除；积分与已完成记录保留。' : deleting.kind === 'scoring' ? '删除后不能用于新任务；已有任务保留原评分。' : '已有兑换与积分记录会保留。'}</Text>
      <Message text={error} /><Button title="确认删除" busy={busy} disabled={loading} onPress={() => { void remove(); }} />
      <Button title="保留" secondary disabled={locked} onPress={() => setDeleting(null)} />
    </Sheet>}
    {redeeming && <Sheet title="兑换奖励" busy={busy} onClose={() => setRedeeming(null)}>
      <Text style={{ color: colors.text, fontSize: 21, fontWeight: '800' }}>{redeeming.title}</Text>
      <Text style={{ color: colors.muted, lineHeight: 23 }}>需要 {redeeming.cost_points} 分，当前有 {user?.current_value ?? 0} 分。</Text>
      <Message text={error} /><Button title="确认兑换" icon="gift" busy={busy} disabled={loading || (user?.current_value ?? 0) < redeeming.cost_points}
        onPress={() => { void controller.redeemReward(redeeming).then(ok => { if (ok) setRedeeming(null); }); }} />
    </Sheet>}
  </Page>;
}

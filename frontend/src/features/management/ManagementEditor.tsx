import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import type { EditableItem } from '../../api/management';
import { Sheet } from '../../components/Sheet';
import { Button, Field, Icon, Message } from '../../components/ui';
import { useTheme } from '../../theme/ThemeProvider';
import { useHome } from '../home/HomeProvider';
import { DateField } from '../tasks/Calendar';
import { goalPayload, rewardPayload, schemePayload, type GoalForm, type LevelForm } from './model';

export function ManagementEditor({ item, onClose }: { item: EditableItem; onClose: () => void }) {
  const { colors } = useTheme();
  const { data, busy, loading, error, controller } = useHome();
  const [title, setTitle] = useState(item.value?.title || '');
  const goal = item.kind === 'goals' ? item.value : undefined;
  const reward = item.kind === 'rewards' ? item.value : undefined;
  const scheme = item.kind === 'scoring' ? item.value : undefined;
  const [dates, setDates] = useState<Omit<GoalForm, 'title'>>({ start: goal?.start_date || data!.progress.today,
    target: goal?.target_date || '', current: goal?.current_value || '', goal: goal?.target_value || '' });
  const [description, setDescription] = useState(reward?.description || '');
  const [cost, setCost] = useState(String(reward?.cost_points ?? ''));
  const [levels, setLevels] = useState<LevelForm[]>(scheme ? Object.entries(scheme.levels_json || {}).map(([name, points]) => ({ name, points: String(points) })) : [{ name: '完成', points: '1' }]);
  const [validation, setValidation] = useState<string | null>(null);
  const labels = { goals: '目标', scoring: '评分方案', rewards: '奖励' };
  const locked = busy || loading;
  const submit = async () => {
    if (locked) return;
    setValidation(null);
    try {
      const ok = item.kind === 'goals' ? await controller.saveGoal(goalPayload({ ...dates, title }), item.value?.id)
        : item.kind === 'scoring' ? await controller.saveScheme(schemePayload(title, levels), item.value?.id)
          : await controller.saveReward(rewardPayload(title, description, cost), item.value?.id);
      if (ok) onClose();
    } catch (failure) { setValidation(failure instanceof Error ? failure.message : '请检查输入。'); }
  };
  return <Sheet title={`${item.value ? '编辑' : '添加'}${labels[item.kind]}`} busy={busy} onClose={onClose}>
    <Field label={`${labels[item.kind]}名称`} icon={item.kind === 'goals' ? 'flag' : item.kind === 'rewards' ? 'gift' : 'layers'}
      value={title} onChangeText={setTitle} placeholder={`给${labels[item.kind]}取个名字`} editable={!locked} maxLength={510} />
    {item.kind === 'goals' && <>
      <DateField label="开始日期" value={dates.start} base={data!.progress.today} today={data!.progress.today} disabled={locked}
        onChange={start => setDates(old => ({ ...old, start }))} />
      <DateField label="目标日期（选填）" value={dates.target} base={dates.start} today={data!.progress.today} disabled={locked} optional
        onChange={target => setDates(old => ({ ...old, target }))} />
      <Field label="当前进度（选填）" icon="activity" value={dates.current} placeholder="例如：每周 1 次" editable={!locked}
        onChangeText={current => setDates(old => ({ ...old, current }))} maxLength={510} />
      <Field label="期望进度（选填）" icon="target" value={dates.goal} placeholder="例如：每周 3 次" editable={!locked}
        onChangeText={goal => setDates(old => ({ ...old, goal }))} maxLength={510} />
    </>}
    {item.kind === 'scoring' && <>
      <Text style={{ color: colors.text, fontWeight: '700', fontSize: 14 }}>评分等级</Text>
      {levels.map((level, index) => <View key={index} style={{ padding: 15, gap: 12, borderRadius: 16, backgroundColor: colors.mutedSurface }}>
        <Field label={`等级 ${index + 1} 名称`} icon="tag" value={level.name} editable={!locked} maxLength={200}
          onChangeText={name => setLevels(old => old.map((row, i) => i === index ? { ...row, name } : row))} />
        <Field label={`等级 ${index + 1} 分数`} icon="award" value={level.points} editable={!locked} keyboardType="numbers-and-punctuation"
          onChangeText={points => setLevels(old => old.map((row, i) => i === index ? { ...row, points } : row))} />
        <Pressable accessibilityRole="button" accessibilityLabel={`移除等级 ${index + 1}`} disabled={locked || levels.length === 1}
          onPress={() => setLevels(old => old.filter((_, i) => i !== index))} style={{ alignSelf: 'flex-end', padding: 8, flexDirection: 'row', gap: 6, opacity: levels.length === 1 ? 0.3 : 1 }}>
          <Icon name="trash-2" color={colors.danger} size={13} /><Text style={{ color: colors.danger, fontSize: 12 }}>移除</Text>
        </Pressable>
      </View>)}
      <Button title="添加等级" secondary icon="plus" disabled={locked} onPress={() => setLevels(old => [...old, { name: '', points: '' }])} />
      {!!item.value && <Text style={{ color: colors.muted, fontSize: 12, lineHeight: 20 }}>已有任务及已生成记录保留原评分。</Text>}
    </>}
    {item.kind === 'rewards' && <>
      <Field label="所需积分" icon="award" value={cost} editable={!locked} keyboardType="number-pad" placeholder="0 或正整数" onChangeText={setCost} />
      <Field label="奖励说明（选填）" icon="align-left" value={description} editable={!locked} multiline placeholder="奖励自己什么？" onChangeText={setDescription} />
      {reward?.status === 'redeemed' && <Text style={{ color: colors.muted, fontSize: 12 }}>历史兑换记录保持原样。</Text>}
    </>}
    <Message text={validation || error} />
    <Button title={`保存${labels[item.kind]}`} icon="check" busy={busy} disabled={loading} onPress={() => { void submit(); }} />
  </Sheet>;
}

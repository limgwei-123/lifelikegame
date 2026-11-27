import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { Page } from '../../components/Page';
import { Sheet } from '../../components/Sheet';
import { Button, Card, Field, Icon, Message } from '../../components/ui';
import { useTheme } from '../../theme/ThemeProvider';
import { useHome } from '../home/HomeProvider';
import { useAI } from './AIProvider';
import { PlanEditor } from './PlanEditor';

export function AIScreen() {
  const { colors } = useTheme();
  const ai = useAI(), home = useHome();
  const [prompt, setPrompt] = useState(''), [confirming, setConfirming] = useState(false), [resetting, setResetting] = useState(false);
  useFocusEffect(useCallback(() => { void home.controller.refresh(); }, [home.controller]));
  const locked = ai.busy || !!ai.pendingId || !!ai.outcome;
  const unavailable = ai.draft?.plan.tasks.some(t => t.scoring_scheme_id !== null && !home.data?.schemes.some(s => s.id === t.scoring_scheme_id));
  const generate = async () => { if (await ai.controller.generate(prompt)) setPrompt(''); };
  return <Page title="AI 规划" footer={ai.outcome ? <Button title="查看首页任务" icon="home" onPress={() => router.navigate('/')} />
    : ai.pendingId ? <Button title="重新核实创建结果" icon="refresh-cw" busy={ai.busy} disabled={home.busy || home.loading} onPress={() => { void ai.controller.retryConfirmation(); }} />
      : ai.draft ? <Button title="确认创建计划" icon="check" busy={ai.busy} disabled={home.busy || home.loading || unavailable} onPress={() => setConfirming(true)} /> : undefined}>
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
      <Pressable accessibilityRole="button" accessibilityLabel="返回我的" onPress={() => router.dismissTo('/me')} style={{ paddingVertical: 12, paddingRight: 10 }}><Icon name="arrow-left" size={21} /></Pressable>
      <Text accessibilityRole="header" style={{ flex: 1, color: colors.text, fontSize: 25, fontWeight: '800' }}>AI 规划</Text>
      {!!ai.messages.length && <Pressable accessibilityRole="button" accessibilityLabel="开始新计划" disabled={ai.busy || !!ai.pendingId} onPress={() => setResetting(true)} style={{ padding: 12 }}><Icon name="plus" size={20} color={colors.muted} /></Pressable>}
    </View>
    {!ai.messages.length && <Card style={{ gap: 16, padding: 26 }}><Icon name="compass" color={colors.accent} size={30} />
      <Text style={{ color: colors.text, fontSize: 22, fontWeight: '800' }}>想开始哪段冒险？</Text>
      <Text style={{ color: colors.muted, lineHeight: 23 }}>告诉我你的目标、可用时间，或想坚持的习惯。</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 9 }}>{['我想每周一三五运动，每次半小时', '我想养成每天阅读的习惯'].map(example =>
        <Pressable key={example} accessibilityRole="button" accessibilityLabel={example} disabled={locked} onPress={() => setPrompt(example)} style={{ padding: 12, backgroundColor: colors.accentSoft, borderRadius: 13 }}>
          <Text style={{ color: colors.accent, fontSize: 12 }}>{example}</Text></Pressable>)}</View>
    </Card>}
    {!!ai.messages.length && <View style={{ gap: 13 }}>{ai.messages.map((message, index) => <View key={index} style={{ maxWidth: '92%', alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start',
      borderRadius: 18, padding: 17, gap: 8, backgroundColor: message.role === 'user' ? colors.accentSoft : colors.surface, borderWidth: 1, borderColor: colors.border }}>
      <Text style={{ color: colors.muted, fontSize: 11 }}>{message.role === 'user' ? '你' : '规划助手'}</Text><Text selectable style={{ color: colors.text, lineHeight: 24, fontSize: 14 }}>{message.content}</Text>
    </View>)}</View>}
    <Message text={ai.error} />
    {!!ai.outcome && <Message success text={ai.outcome === 'confirmed' ? '计划已创建，开始你的行动吧。' : '这份计划已经确认，请到首页或目标查看。'} />}
    {!!ai.outcome && <Message text={home.error} />}
    {ai.draft && <PlanEditor plan={ai.draft.plan} onChange={ai.controller.editPlan} schemes={home.data?.schemes || []} disabled={locked} />}
    {!ai.outcome && !ai.pendingId && <Card style={{ gap: 16 }}>
      <Field label={ai.messages.length ? '补充或调整计划' : '你的目标'} icon="edit-3" multiline value={prompt} onChangeText={setPrompt} editable={!locked} maxLength={8000}
        placeholder="例如：想开始运动，每周有三天时间，每次半小时" />
      <Button title={ai.messages.length ? '发送补充' : '生成计划'} icon="send" busy={ai.busy} disabled={!prompt.trim()} onPress={() => { void generate(); }} />
      <Text style={{ color: colors.muted, fontSize: 11, lineHeight: 19 }}>发送会使用 AI 请求额度；手动编辑计划不会。刷新页面会清空本轮对话。</Text>
    </Card>}
    {confirming && ai.draft && <Sheet title="确认行动计划" busy={ai.busy} onClose={() => setConfirming(false)}>
      <Text style={{ color: colors.text, fontSize: 20, fontWeight: '800' }}>{ai.draft.plan.goal_title}</Text>
      <Text style={{ color: colors.muted, lineHeight: 23 }}>将新建 1 个目标和 {ai.draft.plan.tasks.length} 个任务，从你的今天开始安排。</Text>
      <Message text={ai.error} /><Message text={home.error} />
      <Button title="创建目标和任务" icon="check" busy={ai.busy} disabled={home.busy || home.loading || unavailable}
        onPress={() => { void ai.controller.confirm(ai.draft!.plan).then(() => setConfirming(false)); }} />
    </Sheet>}
    {resetting && <Sheet title="开始新计划" onClose={() => setResetting(false)}>
      <Text style={{ color: colors.muted, lineHeight: 23 }}>清空本轮对话与未确认的计划，已创建的目标和任务会保留。</Text>
      <Button title="开始新计划" onPress={() => { ai.controller.reset(); setPrompt(''); setResetting(false); }} />
    </Sheet>}
  </Page>;
}

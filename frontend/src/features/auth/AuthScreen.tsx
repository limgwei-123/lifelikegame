import { Link, router, useLocalSearchParams } from 'expo-router';
import { useEffect, useRef, useState, type ComponentRef } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View, useWindowDimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Brand, Button, Field, Icon, Message } from '../../components/ui';
import { JourneyArt } from '../../components/JourneyArt';
import { useSession } from '../../session/SessionProvider';
import { useTheme } from '../../theme/ThemeProvider';

export function AuthScreen({ register = false }: { register?: boolean }) {
  const { width } = useWindowDimensions();
  const wide = width >= 900;
  const insets = useSafeAreaInsets();
  const { colors } = useTheme();
  const { controller, pending, error, notice } = useSession();
  const params = useLocalSearchParams<{ email?: string }>();
  const [email, setEmail] = useState(params.email ?? '');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [validation, setValidation] = useState<string | null>(null);
  const passwordRef = useRef<ComponentRef<typeof TextInput>>(null), confirmRef = useRef<ComponentRef<typeof TextInput>>(null);
  const submitting = useRef(false), mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const submit = async () => {
    if (submitting.current || pending) return;
    setValidation(null);
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) { setValidation('请输入有效的邮箱地址。'); return; }
    if (!password) { setValidation('请输入密码。'); return; }
    if (register && (password.length < 8 || password.length > 128 || !password.trim())) {
      setValidation('请使用 8–128 个字符的密码。'); return;
    }
    if (register && password !== confirm) { setValidation('两次输入的密码不一致。'); return; }
    submitting.current = true;
    try {
      if (register) {
        if (await controller.signUp(email, password) && mounted.current) {
          setPassword(''); setConfirm('');
          router.replace({ pathname: '/login', params: { email: email.trim() } });
        }
      } else await controller.signIn(email, password);
    } finally { submitting.current = false; }
  };
  return <KeyboardAvoidingView style={{ flex: 1, backgroundColor: colors.background }}
    behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
    <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={[auth.scroll,
      { paddingTop: Math.max(32, insets.top + 20), paddingBottom: Math.max(28, insets.bottom + 20) }]}>
      <View style={[auth.layout, wide && auth.wide]}>
        {wide && <View style={auth.story}>
          <Brand large />
          <JourneyArt />
          <Text style={[auth.storyTitle, { color: colors.text }]}>把每次行动，{ '\n' }变成一点进步。</Text>
          <Text style={[auth.storyBody, { color: colors.muted }]}>你的目标，你的冒险。</Text>
        </View>}
        <View style={[auth.form, { backgroundColor: colors.surface, borderColor: colors.border }, !wide && auth.phoneForm]}>
          {!wide && <View style={{ marginBottom: 31 }}><Brand large /></View>}
          <View style={[auth.eyebrow, { backgroundColor: colors.accentSoft }]}>
            <Icon name={register ? 'flag' : 'sun'} size={15} color={colors.accent} />
            <Text style={{ color: colors.accent, fontSize: 12, fontWeight: '600' }}>{register ? '新的开始' : '继续你的旅程'}</Text>
          </View>
          <Text accessibilityRole="header" style={[auth.title, { color: colors.text }]}>{register ? '创建你的账号' : '欢迎回来'}</Text>
          <Text style={[auth.subtitle, { color: colors.muted }]}>{register ? '从今天开始，记录每一点进步。' : '登录后，继续自己的冒险。'}</Text>
          <View style={auth.fields}>
            <Field label="邮箱" icon="mail" value={email} onChangeText={setEmail} placeholder="you@example.com"
              keyboardType="email-address" autoCapitalize="none" autoCorrect={false} autoComplete="email"
              textContentType="emailAddress" returnKeyType="next" onSubmitEditing={() => passwordRef.current?.focus()} editable={!pending} />
            <Field label="密码" icon="lock" secret value={password} onChangeText={setPassword}
              placeholder={register ? '至少 8 个字符' : '请输入密码'} inputRef={passwordRef}
              autoCapitalize="none" autoCorrect={false} autoComplete={register ? 'new-password' : 'current-password'}
              textContentType={register ? 'newPassword' : 'password'} returnKeyType={register ? 'next' : 'go'}
              onSubmitEditing={() => { if (register) confirmRef.current?.focus(); else void submit(); }} editable={!pending} />
            {register && <Field label="确认密码" icon="shield" secret value={confirm} onChangeText={setConfirm}
              placeholder="再输入一次密码" inputRef={confirmRef} autoCapitalize="none" autoCorrect={false}
              autoComplete="new-password" textContentType="newPassword" returnKeyType="go"
              onSubmitEditing={() => { void submit(); }} editable={!pending} />}
          </View>
          <Message text={validation ?? error} />
          {!register && <Message text={notice} success />}
          <Button title={register ? '创建账号' : '登录'} icon="arrow-right" busy={pending} onPress={() => { void submit(); }} />
          <View style={auth.switcher}>
            <Text style={{ color: colors.muted, fontSize: 13 }}>{register ? '已经有账号？' : '还没有账号？'}</Text>
            <Link href={register ? '/login' : '/register'} replace asChild>
              <Pressable accessibilityRole="link" disabled={pending} style={auth.link}>
                <Text style={{ color: colors.accent, fontWeight: '700', fontSize: 13 }}>{register ? '返回登录' : '创建账号'}</Text>
              </Pressable>
            </Link>
          </View>
        </View>
      </View>
    </ScrollView>
  </KeyboardAvoidingView>;
}
const auth = StyleSheet.create({
  scroll: { flexGrow: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 20 },
  layout: { width: '100%', maxWidth: 470 },
  wide: { maxWidth: 1020, flexDirection: 'row', alignItems: 'center', gap: 90, paddingHorizontal: 25 },
  story: { flex: 1, alignItems: 'flex-start', gap: 15, paddingBottom: 30 },
  storyTitle: { fontSize: 35, fontWeight: '800', lineHeight: 51, letterSpacing: -1 },
  storyBody: { fontSize: 15, lineHeight: 25 },
  form: { flex: 1, padding: 36, borderRadius: 28, borderWidth: 1, gap: 16, maxWidth: 450 },
  phoneForm: { padding: 25 },
  eyebrow: { flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-start', gap: 7, paddingHorizontal: 10, paddingVertical: 7, borderRadius: 20 },
  title: { fontSize: 28, fontWeight: '800', letterSpacing: -0.7, marginTop: 4 },
  subtitle: { fontSize: 13, lineHeight: 21, marginTop: -8 },
  fields: { gap: 19, marginTop: 15, marginBottom: 5 },
  switcher: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 3 },
  link: { paddingHorizontal: 7, paddingVertical: 13 },
});

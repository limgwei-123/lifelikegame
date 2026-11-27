import { useRef, useState, type ComponentRef } from 'react';
import { Text, TextInput, View } from 'react-native';
import { Sheet } from '../../components/Sheet';
import { Button, Field, Message } from '../../components/ui';
import { useTheme } from '../../theme/ThemeProvider';
import { useHome } from '../home/HomeProvider';
import { passwordErrors } from './model';

export function PasswordSheet({ onClose }: { onClose: () => void }) {
  const { colors } = useTheme();
  const { busy, loading, error, controller } = useHome();
  const [current, setCurrent] = useState(''), [next, setNext] = useState(''), [confirm, setConfirm] = useState('');
  const [fields, setFields] = useState<ReturnType<typeof passwordErrors>>({});
  const nextRef = useRef<ComponentRef<typeof TextInput>>(null), confirmRef = useRef<ComponentRef<typeof TextInput>>(null);
  const locked = busy || loading;
  const submit = async () => {
    if (locked) return;
    const errors = passwordErrors(current, next, confirm); setFields(errors);
    if (Object.keys(errors).length) return;
    await controller.changePassword(current, next);
  };
  return <Sheet title="修改密码" busy={busy} onClose={onClose}>
    <View style={{ gap: 9 }}>
      <Field label="当前密码" icon="lock" secret value={current} onChangeText={setCurrent} editable={!locked}
        autoCapitalize="none" autoCorrect={false} autoComplete="current-password" textContentType="password" returnKeyType="next"
        onSubmitEditing={() => nextRef.current?.focus()} aria-invalid={!!fields.current || error === '当前密码不正确。'} />
      <Message text={fields.current || (error === '当前密码不正确。' ? error : null)} />
    </View>
    <View style={{ gap: 9 }}>
      <Field label="新密码" icon="key" secret value={next} onChangeText={setNext} editable={!locked} inputRef={nextRef}
        autoCapitalize="none" autoCorrect={false} autoComplete="new-password" textContentType="newPassword" returnKeyType="next"
        maxLength={256} onSubmitEditing={() => confirmRef.current?.focus()} aria-invalid={!!fields.next} />
      <Message text={fields.next || null} />
    </View>
    <View style={{ gap: 9 }}>
      <Field label="确认新密码" icon="shield" secret value={confirm} onChangeText={setConfirm} editable={!locked} inputRef={confirmRef}
        autoCapitalize="none" autoCorrect={false} autoComplete="new-password" textContentType="newPassword" returnKeyType="go"
        maxLength={256} onSubmitEditing={() => { void submit(); }} aria-invalid={!!fields.confirm} />
      <Message text={fields.confirm || null} />
    </View>
    <Text style={{ color: colors.muted, fontSize: 12, lineHeight: 20 }}>使用 8–128 个字符。修改成功后需要重新登录。</Text>
    <Message text={error === '当前密码不正确。' ? null : error} />
    <Button title="更新密码" icon="check" busy={busy} disabled={loading} onPress={() => { void submit(); }} />
  </Sheet>;
}

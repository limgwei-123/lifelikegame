import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { Chip } from '../../components/Chip';
import { Sheet } from '../../components/Sheet';
import { Button, Field, Icon, Message } from '../../components/ui';
import { useSession } from '../../session/SessionProvider';
import { useTheme } from '../../theme/ThemeProvider';
import { useHome } from '../home/HomeProvider';
import { avatars, ProfileValidationError, profilePayload, type ProfileForm } from './model';
import { UserAvatar } from './UserAvatar';

const zones = [
  ['吉隆坡', 'Asia/Kuala_Lumpur'], ['新加坡', 'Asia/Singapore'], ['上海', 'Asia/Shanghai'],
  ['东京', 'Asia/Tokyo'], ['伦敦', 'Europe/London'], ['洛杉矶', 'America/Los_Angeles'], ['UTC', 'UTC'],
];
export function ProfileSheet({ onClose }: { onClose: () => void }) {
  const { user } = useSession();
  const { colors } = useTheme();
  const { busy, loading, error, controller } = useHome();
  const [form, setForm] = useState<ProfileForm>({ name: user?.display_name || '', avatar: user?.avatar_key || 'leaf', timezone: user!.timezone });
  const [fields, setFields] = useState<ProfileValidationError['fields']>({});
  const [submitting, setSubmitting] = useState(false);
  const locked = busy || loading || submitting;
  const submit = async () => {
    if (locked) return;
    setFields({});
    try {
      const payload = profilePayload(form);
      setSubmitting(true);
      if (await controller.saveProfile(payload)) onClose();
    } catch (failure) {
      if (failure instanceof ProfileValidationError) setFields(failure.fields);
    } finally { setSubmitting(false); }
  };
  return <Sheet title="个人资料" busy={busy || submitting} onClose={onClose}>
    <View style={{ alignItems: 'center', gap: 12 }}><UserAvatar avatarKey={form.avatar} size={84} />
      <Text selectable style={{ color: colors.muted, fontSize: 13 }}>{user?.email}</Text>
    </View>
    <View style={{ gap: 10 }}>
      <Field label="昵称（选填）" icon="user" placeholder="冒险者" value={form.name} maxLength={120} editable={!locked}
        onChangeText={name => setForm(old => ({ ...old, name }))} aria-invalid={!!fields.name} />
      <Message text={fields.name || null} />
      <Text style={{ color: colors.muted, fontSize: 11 }}>最多 30 个字，留空使用默认名称。</Text>
    </View>
    <View style={{ gap: 12 }}>
      <Text style={{ color: colors.text, fontWeight: '600', fontSize: 13 }}>头像</Text>
      <View style={{ flexDirection: 'row', gap: 8 }}>
        {avatars.map(avatar => <Pressable key={avatar.key} accessibilityRole="button" accessibilityLabel={`头像：${avatar.name}`}
          aria-pressed={form.avatar === avatar.key} disabled={locked} onPress={() => setForm(old => ({ ...old, avatar: avatar.key }))}
          style={{ flex: 1, alignItems: 'center', borderWidth: form.avatar === avatar.key ? 1.5 : 1,
            borderColor: form.avatar === avatar.key ? colors.accent : colors.border, borderRadius: 15, paddingVertical: 12, gap: 9 }}>
          <UserAvatar avatarKey={avatar.key} size={42} />
          <Text style={{ color: form.avatar === avatar.key ? colors.accent : colors.muted, fontSize: 11 }}>{avatar.name}</Text>
        </Pressable>)}
      </View>
      <Message text={fields.avatar || null} />
    </View>
    <View style={{ gap: 10 }}>
      <Field label="时区" icon="globe" value={form.timezone} onChangeText={timezone => setForm(old => ({ ...old, timezone }))}
        autoCapitalize="none" autoCorrect={false} maxLength={64} editable={!locked} aria-invalid={!!fields.timezone} />
      <Message text={fields.timezone || null} />
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 7 }}>{zones.map(([label, timezone]) =>
        <Chip key={timezone} label={label} selected={form.timezone === timezone} disabled={locked} onPress={() => setForm(old => ({ ...old, timezone }))} />)}</View>
      <View style={{ flexDirection: 'row', gap: 7, alignItems: 'center' }}><Icon name="info" size={13} color={colors.muted} />
        <Text style={{ color: colors.muted, fontSize: 11, flex: 1, lineHeight: 18 }}>时区会影响“今天”和连续行动的日期。</Text>
      </View>
    </View>
    <Message text={error} />
    <Button title="保存资料" icon="check" busy={busy || submitting} disabled={loading} onPress={() => { void submit(); }} />
  </Sheet>;
}

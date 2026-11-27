import { createContext, useContext, useEffect, useState, useSyncExternalStore, type PropsWithChildren } from 'react';
import { ActivityIndicator, View, useColorScheme } from 'react-native';
import { AppearanceController, type Preferences } from './controller';
import { preferenceStore } from './storage';

const light = {
  background: '#f5f7fc', surface: '#ffffff', mutedSurface: '#edf1f8', text: '#172942', muted: '#75849d',
  border: '#dfe6f2', accent: '#365dce', accentSoft: '#e9efff', accentText: '#ffffff',
  success: '#39745b', successSoft: '#eaf5ee', danger: '#b44343', dangerSoft: '#fff0ef',
};
const dark: typeof light = {
  background: '#101722', surface: '#192333', mutedSurface: '#202e42', text: '#eef3fd', muted: '#a0aec5',
  border: '#2d3c52', accent: '#9cb7ff', accentSoft: '#253a62', accentText: '#13243e',
  success: '#9ed2b0', successSoft: '#213b30', danger: '#ffb6b1', dangerSoft: '#422c31',
};
const accents = {
  blue: { light: ['#365dce', '#e9efff', '#ffffff'], dark: ['#9cb7ff', '#253a62', '#13243e'] },
  green: { light: ['#247a60', '#e6f4ee', '#ffffff'], dark: ['#8bd4ba', '#1c3c32', '#102c23'] },
  purple: { light: ['#7550ba', '#efe9fa', '#ffffff'], dark: ['#c5adff', '#35294b', '#231538'] },
  orange: { light: ['#b45a20', '#fff0e4', '#ffffff'], dark: ['#ffbc86', '#463225', '#321c0c'] },
};
interface ThemeContextValue {
  colors: typeof light; isDark: boolean; preferences: Preferences; saving: boolean; error: string | null;
  setPreferences: (value: Preferences) => Promise<boolean>;
}
const ThemeContext = createContext<ThemeContextValue | null>(null);
export function ThemeProvider({ children }: PropsWithChildren) {
  const systemDark = useColorScheme() === 'dark';
  const [controller] = useState(() => new AppearanceController(preferenceStore));
  const state = useSyncExternalStore(controller.subscribe, controller.getSnapshot, controller.getServerSnapshot);
  useEffect(() => { void controller.restore(); }, [controller]);
  const isDark = state.preferences.mode === 'system' ? systemDark : state.preferences.mode === 'dark';
  const [accent, accentSoft, accentText] = accents[state.preferences.accent][isDark ? 'dark' : 'light'];
  const colors = { ...(isDark ? dark : light), accent, accentSoft, accentText };
  return <ThemeContext.Provider value={{ colors, isDark, preferences: state.preferences, saving: state.saving, error: state.error, setPreferences: controller.save }}>
    {state.ready ? children : <View style={{ flex: 1, justifyContent: 'center', backgroundColor: colors.background }}><ActivityIndicator color={colors.accent} /></View>}
  </ThemeContext.Provider>;
}
export function useTheme() {
  const value = useContext(ThemeContext);
  if (!value) throw new Error('ThemeProvider is required');
  return value;
}

import { createContext, useContext, type PropsWithChildren } from 'react';
import { useColorScheme } from 'react-native';

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
const ThemeContext = createContext({ colors: light, isDark: false });
export function ThemeProvider({ children }: PropsWithChildren) {
  const isDark = useColorScheme() === 'dark';
  return <ThemeContext.Provider value={{ colors: isDark ? dark : light, isDark }}>{children}</ThemeContext.Provider>;
}
export const useTheme = () => useContext(ThemeContext);

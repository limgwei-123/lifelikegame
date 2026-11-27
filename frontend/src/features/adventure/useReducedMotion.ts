import { useEffect, useState } from 'react';
import { AccessibilityInfo, Platform } from 'react-native';

export function useReducedMotion() {
  // Stay still until the platform preference is known.
  const [reduced, setReduced] = useState(true);
  useEffect(() => {
    if (Platform.OS === 'web') {
      const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
      setReduced(preference.matches);
      const update = () => setReduced(preference.matches);
      preference.addEventListener('change', update);
      return () => preference.removeEventListener('change', update);
    }
    let mounted = true, changed = false;
    void AccessibilityInfo.isReduceMotionEnabled().then(value => { if (mounted && !changed) setReduced(value); }).catch(() => {});
    const subscription = AccessibilityInfo.addEventListener('reduceMotionChanged', value => { changed = true; setReduced(value); });
    return () => { mounted = false; subscription.remove(); };
  }, []);
  return reduced;
}

import { createContext, useContext, useEffect, useState, useSyncExternalStore, type PropsWithChildren } from 'react';
import { AppState, Platform, View } from 'react-native';
import { useSession } from '../../session/SessionProvider';
import { HomeController } from './controller';
import { CompletionToast } from '../adventure/CompletionToast';

const HomeContext = createContext<HomeController | null>(null);
export function HomeProvider({ children }: PropsWithChildren) {
  const { controller: session } = useSession();
  const [controller] = useState(() => new HomeController(session));
  useEffect(() => {
    controller.activate();
    const refresh = () => { void controller.refresh(true); };
    const listener = AppState.addEventListener('change', state => { if (state === 'active') refresh(); });
    const visible = () => { if (document.visibilityState === 'visible') refresh(); };
    if (Platform.OS === 'web') document.addEventListener('visibilitychange', visible);
    return () => {
      listener.remove();
      if (Platform.OS === 'web') document.removeEventListener('visibilitychange', visible);
      controller.stop();
    };
  }, [controller]);
  return <HomeContext.Provider value={controller}><View style={{ flex: 1 }}>{children}<FeedbackLayer /></View></HomeContext.Provider>;
}
function FeedbackLayer() {
  const { feedback, controller } = useHome();
  return feedback ? <CompletionToast feedback={feedback} onDismiss={controller.clearFeedback} /> : null;
}
export function useHome() {
  const controller = useContext(HomeContext);
  if (!controller) throw new Error('HomeProvider is required');
  const state = useSyncExternalStore(controller.subscribe, controller.getSnapshot, controller.getSnapshot);
  return { ...state, controller };
}

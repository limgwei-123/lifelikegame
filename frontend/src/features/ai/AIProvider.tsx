import { createContext, useContext, useEffect, useState, useSyncExternalStore, type PropsWithChildren } from 'react';
import { useSession } from '../../session/SessionProvider';
import type { HomeController } from '../home/controller';
import { AIController } from './controller';

const Context = createContext<AIController | null>(null);
export function AIProvider({ home, children }: PropsWithChildren<{ home: HomeController }>) {
  const { controller: session } = useSession();
  const [controller] = useState(() => new AIController(session, home.confirmAiDraft));
  useEffect(() => { controller.activate(); return controller.stop; }, [controller]);
  return <Context.Provider value={controller}>{children}</Context.Provider>;
}
export function useAI() {
  const controller = useContext(Context); if (!controller) throw new Error('AIProvider is required');
  const state = useSyncExternalStore(controller.subscribe, controller.getSnapshot, controller.getSnapshot);
  return { ...state, controller };
}

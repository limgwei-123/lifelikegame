import { createContext, useContext, useEffect, useState, useSyncExternalStore, type PropsWithChildren } from 'react';
import { apiBaseUrl } from '../api/config';
import { SessionController } from './controller';
import { tokenStore } from './token';

const SessionContext = createContext<SessionController | null>(null);
export function SessionProvider({ children }: PropsWithChildren) {
  const [controller] = useState(() => new SessionController(tokenStore, apiBaseUrl()));
  useEffect(() => { void controller.restore(); return controller.stop; }, [controller]);
  return <SessionContext.Provider value={controller}>{children}</SessionContext.Provider>;
}
export function useSession() {
  const controller = useContext(SessionContext);
  if (!controller) throw new Error('SessionProvider is required');
  const state = useSyncExternalStore(controller.subscribe, controller.getSnapshot, controller.getServerSnapshot);
  return { ...state, controller, api: controller.api };
}

import { Redirect } from 'expo-router';
import { useSession } from '../src/session/SessionProvider';
export default function NotFound() {
  const { status } = useSession();
  return <Redirect href={status === 'signedIn' ? '/' : '/login'} />;
}

import { redirect } from 'next/navigation';
import { allowed } from '@/lib/session';
import Workspace from './workspace';

export default async function Home() { if (!(await allowed())) redirect('/login'); return <Workspace />; }

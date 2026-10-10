import { notFound, redirect } from 'next/navigation';
import { allowed } from '@/lib/session';
import Workspace, { type View } from '../workspace';

const views = new Set(['dashboard', 'discover', 'leads', 'tasks', 'workflows', 'lab', 'chat', 'settings']);
export default async function Section({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  if (!views.has(section)) notFound();
  if (!(await allowed())) redirect('/login');
  return <Workspace initialView={section as View} />;
}

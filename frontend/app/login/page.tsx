import { redirect } from 'next/navigation';
import { allowed } from '@/lib/session';
import Login from './login';
import './auth.css';

export default async function Page() { if (await allowed()) redirect('/'); return <Login />; }

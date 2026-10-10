import type { Metadata } from 'next';
import './globals.css';
import './additions.css';
import './polish.css';

export const metadata: Metadata = { title: 'AIAutomation | Med spa workspace', description: 'Research, review and sandbox automation for med spas' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}

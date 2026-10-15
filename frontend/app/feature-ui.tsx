'use client';
import type { ReactNode } from 'react';

export type Row = Record<string, any>;
export async function api(path: string, init?: RequestInit): Promise<any> {
  const response = await fetch('/api/backend/' + path.replace(/^\//, ''), { cache: 'no-store', ...init });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const message = data?.error?.message || data?.error || data?.detail;
    throw new Error(typeof message === 'string' ? message : `Request failed (${response.status})`);
  }
  return data;
}
export const json = (body: object, method = 'POST'): RequestInit => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
export const date = (value?: string) => value ? new Date(value).toLocaleString() : 'Not recorded';
export const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'Could not complete this operation';
export function Badge({ children, tone = '' }: { children: ReactNode; tone?: string }) { return <span className={'badge ' + tone}>{children}</span>; }
export function Notice({ error }: { error: string }) { return error ? <div className="notice error" role="alert">{error}</div> : null; }
export function Empty({ children }: { children: ReactNode }) { return <div className="empty">{children}</div>; }
export function Result({ value }: { value: Row }) { return <details className="result-details"><summary>Recorded result</summary><pre className="output">{JSON.stringify(value, null, 2)}</pre></details>; }

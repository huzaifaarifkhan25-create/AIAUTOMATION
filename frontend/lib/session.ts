import { createHmac, timingSafeEqual } from 'node:crypto';
import { cookies } from 'next/headers';

const name = 'aia_session';

function secret() {
  const value = process.env.FRONTEND_SESSION_SECRET;
  if (!value || value.length < 32) throw new Error('FRONTEND_SESSION_SECRET must contain at least 32 characters');
  return value;
}

function signature(value: string) { return createHmac('sha256', secret()).update(value).digest('hex'); }

export async function allowed() {
  const raw = (await cookies()).get(name)?.value || '';
  const [expiry, mac] = raw.split('.');
  if (!expiry || !mac || !/^\d+$/.test(expiry) || Number(expiry) < Date.now() || mac.length !== 64) return false;
  const expected = Buffer.from(signature(expiry), 'hex');
  const actual = Buffer.from(mac, 'hex');
  return actual.length === expected.length && timingSafeEqual(actual, expected);
}

export function validateCode(code: string) {
  const expected = process.env.DEMO_ACCESS_CODE;
  if (!expected || expected.length < 12) throw new Error('DEMO_ACCESS_CODE must contain at least 12 characters');
  const a = Buffer.from(code); const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

export async function openSession() {
  const expiry = String(Date.now() + 8 * 60 * 60 * 1000);
  (await cookies()).set(name, `${expiry}.${signature(expiry)}`, { httpOnly: true, secure: process.env.NODE_ENV === 'production', sameSite: 'strict', path: '/', maxAge: 8 * 60 * 60 });
}

export async function closeSession() { (await cookies()).delete(name); }

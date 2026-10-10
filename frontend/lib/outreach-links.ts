export function mailtoHref(recipient: string, subject: string, body: string) {
  const address = recipient.trim();
  if (address && (!/^[^\s@?&]+@[^\s@?&]+\.[^\s@?&]+$/.test(address) || address.length > 254)) return null;
  return `mailto:${encodeURIComponent(address)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

export function telHref(value: string) {
  const phone = value.replace(/[\s().-]/g, '');
  return /^\+?[0-9]{7,15}$/.test(phone) ? `tel:${phone}` : null;
}

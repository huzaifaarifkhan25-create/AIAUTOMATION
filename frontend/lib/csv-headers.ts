/** Read only the first CSV record; the backend remains the authoritative parser. */
export function csvHeaders(text: string): string[] {
  const columns: string[] = []; let value = ''; let quoted = false;
  const source = text.replace(/^\uFEFF/, '');
  for (let i = 0; i < source.length; i++) {
    const char = source[i];
    if (char === '"') { if (quoted && source[i + 1] === '"') { value += '"'; i++; } else quoted = !quoted; }
    else if (char === ',' && !quoted) { columns.push(value); value = ''; }
    else if ((char === '\n' || char === '\r') && !quoted) { columns.push(value); break; }
    else value += char;
    if (i === source.length - 1) columns.push(value);
  }
  if (!columns.length || columns.length > 80 || columns.some(c => !c || c.length > 200) || new Set(columns).size !== columns.length || quoted) throw Error('CSV headers must be unique, nonempty and valid, with at most 80 columns.');
  return columns;
}
const aliases: Record<string, string[]> = {
  name: ['name', 'title', 'businessname', 'companyname', 'placename'], address: ['address', 'fulladdress', 'businessaddress', 'formattedaddress'],
  website: ['website', 'site', 'websiteurl', 'businesswebsite'], phone: ['phone', 'phonenumber', 'telephone', 'businessphone'],
  rating: ['rating', 'reviewrating', 'starrating', 'averagerating'], review_count: ['reviewcount', 'reviews', 'numberofreviews', 'userstotal', 'userratingcount'],
  place_id: ['placeid', 'googleplaceid'], listing_url: ['link', 'mapsurl', 'googlemapsurl', 'listingurl'],
};
export function suggestedMapping(headers: string[]): Record<string, string> {
  return Object.fromEntries(Object.entries(aliases).map(([field, names]) => {
    const matches = headers.filter(h => names.includes(h.toLowerCase().replace(/[^a-z0-9]/g, '')));
    return [field, matches.length === 1 ? matches[0] : ''];
  }));
}

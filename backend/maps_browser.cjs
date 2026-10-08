// Small live Google Maps pilot. Uses the pinned image's Playwright and browser.
// No fixture fallback, API key, messages, or calls. TLS verification stays on.
const fs = require('fs');
const crypto = require('crypto');
const { chromium } = require('/opt/ms-playwright-go/package');
const outDir = process.env.MAPS_OUTPUT_DIR || '/out';
const redact = message => String(message).replace(/(https?|socks5h?):\/\/[^/\s@]+@/gi, '$1://[redacted]@');
let activeBrowser;
process.on('SIGTERM', async () => {
  const forced = setTimeout(() => process.exit(1), 8000);
  try { await activeBrowser?.close(); } finally { clearTimeout(forced); process.exit(1); }
});

async function collect() {
  const query = fs.readFileSync(`${outDir}/queries.txt`, 'utf8').trim();
  const limit = Number(process.argv[2] || 5);
  if (!query || !Number.isInteger(limit) || limit < 1 || limit > 10) {
    throw new Error('A query and pilot limit of 1–10 are required');
  }
  const startedAt = new Date().toISOString();
  const proxyValue = process.env.HTTPS_PROXY || process.env.HTTP_PROXY || process.env.ALL_PROXY;
  const proxyURL = proxyValue ? new URL(proxyValue) : null;
  const proxy = proxyURL ? {
    server: `${proxyURL.protocol}//${proxyURL.host}`,
    ...(proxyURL.username ? {
      username: decodeURIComponent(proxyURL.username),
      password: decodeURIComponent(proxyURL.password),
    } : {}),
  } : undefined;
  const browser = await chromium.launch({ headless: true, proxy, args: ['--no-sandbox'] });
  activeBrowser = browser;
  const watchdog = setTimeout(() => browser.close().catch(() => {}), 270000);
  const records = [];
  const failures = [];
  try {
    const context = await browser.newContext({ ignoreHTTPSErrors: false, locale: 'en-US' });
    const page = await context.newPage();
    const searchURL = `https://www.google.com/maps/search/${encodeURIComponent(query)}/?hl=en`;
    const response = await page.goto(searchURL, { waitUntil: 'domcontentloaded', timeout: 60000 });
    if (!response || response.status() >= 400) throw new Error('Maps search returned an error');
    await page.locator('a[href*="/maps/place/"]').first().waitFor({ timeout: 30000 });
    await page.screenshot({ path: `${outDir}/search.png`, fullPage: true });
    fs.writeFileSync(`${outDir}/search.html`, await page.content());
    const candidates = await page.locator('a[href*="/maps/place/"]').evaluateAll(nodes =>
      nodes.map(node => ({ name: node.getAttribute('aria-label'), url: node.href })));
    const unique = [...new Map(candidates.filter(c => c.name).map(c => [c.url, c])).values()].slice(0, limit);
    for (const [index, candidate] of unique.entries()) {
      try {
        const url = new URL(candidate.url);
        if (url.protocol !== 'https:' || url.hostname !== 'www.google.com' || !url.pathname.startsWith('/maps/place/')) {
          throw new Error('Unexpected listing destination');
        }
        const listingResponse = await page.goto(url.href, { waitUntil: 'domcontentloaded', timeout: 45000 });
        if (!listingResponse || listingResponse.status() >= 400) throw new Error('Listing returned an error');
        await page.locator('h1').first().waitFor({ timeout: 20000 });
        await page.locator('button[data-item-id="address"]').first().waitFor({ timeout: 15000 });
        const record = await page.evaluate(() => {
          const node = selector => document.querySelector(selector);
          const label = selector => node(selector)?.getAttribute('aria-label') || '';
          const text = selector => node(selector)?.textContent?.trim() || '';
          const ratingArea = node('.F7nice');
          const rating = ratingArea?.querySelector('span[aria-hidden="true"]')?.textContent?.trim() || '';
          const reviews = ratingArea?.querySelector('span[aria-label*="reviews"]')?.getAttribute('aria-label') || '';
          return {
            title: text('h1'),
            address: label('button[data-item-id="address"]').replace(/^Address:\s*/i, '').trim(),
            website: node('a[data-item-id="authority"]')?.href || '',
            phone: label('button[data-item-id^="phone:tel:"]').replace(/^Phone:\s*/i, '').trim(),
            review_rating: /^\d(?:\.\d+)?$/.test(rating) ? rating : '',
            review_count: /^[\d,]+ reviews?$/i.test(reviews) ? reviews.replace(/ reviews?$/i, '').replace(/,/g, '') : '',
            category: text('button.DkEaL'),
          };
        });
        if (!record.title || !record.address) throw new Error('Listing name or address was unavailable');
        if (record.title.normalize('NFKC').trim() !== candidate.name.normalize('NFKC').trim()) {
          throw new Error('Search and listing names did not match');
        }
        const decodedURL = decodeURIComponent(url.href);
        const placeID = decodedURL.match(/!19s(ChIJ[A-Za-z0-9_-]+)/)?.[1] || '';
        record.place_id = placeID;
        record.link = url.href;
        record.collected_at = new Date().toISOString();
        const prefix = `listing-${index + 1}`;
        fs.writeFileSync(`${outDir}/${prefix}.html`, await page.content());
        fs.writeFileSync(`${outDir}/${prefix}.txt`, await page.locator('body').innerText());
        await page.screenshot({ path: `${outDir}/${prefix}.png`, fullPage: true });
        record.evidence_file = `${prefix}.html`;
        records.push(record);
        console.log(`Collected live listing ${index + 1}: ${record.title}`);
      } catch (error) {
        failures.push({ name: candidate.name, error: redact(error.message) });
        console.error(`Listing ${index + 1} could not be collected`);
      }
    }
    if (!records.length) throw new Error('No live listings collected; no CSV was produced');
    const columns = ['title', 'address', 'website', 'phone', 'review_rating', 'review_count', 'place_id', 'link', 'category', 'collected_at'];
    const quote = value => `"${String(value ?? '').replace(/"/g, '""')}"`;
    const csv = [columns.join(','), ...records.map(row => columns.map(key => quote(row[key])).join(','))].join('\n') + '\n';
    fs.writeFileSync(`${outDir}/results.csv`, csv);
    fs.writeFileSync(`${outDir}/manifest.json`, JSON.stringify({
      collector: 'aiautomation-browser-pilot-v1', query, started_at: startedAt,
      finished_at: new Date().toISOString(), search_url: searchURL,
      candidate_count: candidates.length, collected_count: records.length,
      sha256: crypto.createHash('sha256').update(csv).digest('hex'),
      tls_verification: true, complete_directory: false,
      records, failures,
    }, null, 2));
  } finally {
    clearTimeout(watchdog);
    await browser.close();
  }
}

collect().catch(error => {
  // Avoid leaking a proxy URL from an exception.
  console.error(redact(error.message));
  process.exitCode = 1;
});

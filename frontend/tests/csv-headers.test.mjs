import test from 'node:test';
import assert from 'node:assert/strict';
import { csvHeaders, suggestedMapping } from '../lib/csv-headers.ts';

test('CSV header mapping preserves exact quoted headers and ignores later records', () => {
  const headers = csvHeaders('\uFEFF"Business, name","Street ""address""",Website\r\n"Example","Road",https://example.com\r\n');
  assert.deepEqual(headers, ['Business, name', 'Street "address"', 'Website']);
  assert.equal(suggestedMapping(headers).website, 'Website');
  assert.equal(suggestedMapping(headers).address, '');
});

test('ambiguous aliases require manual review; duplicate and malformed headers reject', () => {
  assert.equal(suggestedMapping(['Name', 'Title', 'Address']).name, '');
  assert.throws(() => csvHeaders('Name,Name,Address\n'), /unique/);
  assert.throws(() => csvHeaders('"Name,Address\n'), /valid/);
  assert.throws(() => csvHeaders('Name,,Address\n'), /nonempty/);
});

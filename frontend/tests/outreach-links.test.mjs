import test from 'node:test';
import assert from 'node:assert/strict';
import { mailtoHref, telHref } from '../lib/outreach-links.ts';

test('mailto keeps Urdu and reserved characters in encoded subject and body', () => {
  const href = mailtoHref('owner@example.com', 'سلام & review?', 'Hello = خوش آمدید\nSee you & thanks');
  assert.equal(href, 'mailto:owner%40example.com?subject=%D8%B3%D9%84%D8%A7%D9%85%20%26%20review%3F&body=Hello%20%3D%20%D8%AE%D9%88%D8%B4%20%D8%A2%D9%85%D8%AF%DB%8C%D8%AF%0ASee%20you%20%26%20thanks');
  assert.equal(mailtoHref('', 'Subject', 'Body')?.startsWith('mailto:?subject='), true);
  assert.equal(mailtoHref('bad?cc=other@example.com', 'Subject', 'Body'), null);
});

test('tel accepts listed public numbers only when syntactically usable', () => {
  assert.equal(telHref('+92 (300) 123-4567'), 'tel:+923001234567');
  assert.equal(telHref('call me;123'), null);
  assert.equal(telHref('123'), null);
});

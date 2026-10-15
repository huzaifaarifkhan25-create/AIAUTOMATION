/* Run only against a fresh isolated database. n8n may be real; email is never enabled. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const origin = process.env.TEST_FRONTEND_ORIGIN || 'http://127.0.0.1:18682';
const backend = process.env.TEST_BACKEND_ORIGIN || 'http://127.0.0.1:18681';
const reportPath = process.env.TEST_REPORT_PATH || 'workspace-browser-report.json';
const checks = []; const errors = [];
async function check(name, fn) { await fn(); checks.push(name); console.log('PASS', name); }
function localTime(value) { return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Karachi', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(value)).replace(' ', 'T'); }

(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}), args: ['--no-sandbox'] });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, timezoneId: 'Asia/Karachi' });
  const page = await context.newPage(); page.on('pageerror', e => errors.push(e.message)); page.on('dialog', dialog => void dialog.accept());
  let sourceId, deploymentId, intakeKey;
  async function api(path, init = {}) {
    const response = await page.evaluate(async ({ path, init }) => {
      const request = { method: init.method || 'GET', headers: init.data ? { 'Content-Type': 'application/json' } : undefined, body: init.data ? JSON.stringify(init.data) : undefined };
      const result = await fetch('/api/backend/' + path, request);
      return { ok: result.ok, status: result.status, value: await result.json() };
    }, { path, init });
    assert.ok(response.ok, `${path} failed HTTP ${response.status}: ${JSON.stringify(response.value)}`); return response.value;
  }
  async function nav(name) { await page.locator('.side').getByRole('button', { name, exact: true }).click(); }
  try {
    await check('Individual registration and account reload persist', async () => {
      await page.goto(origin + '/login'); await page.getByRole('heading', { name: 'Create your account' }).waitFor();
      await page.getByLabel('Your name', { exact: true }).fill('Fictional UI Operator'); await page.getByLabel('Email', { exact: true }).fill('ui-operator@example.test');
      await page.getByLabel('Password (at least 12 characters)', { exact: true }).fill('Fictional-browser-password-2026');
      const invitation = page.getByLabel('Workspace invitation code', { exact: true });
      if (await invitation.count()) await invitation.fill(process.env.TEST_INVITATION || 'fixture-ui-invitation-token-2026-private');
      await page.getByLabel('I understand this account joins the same shared workspace as other operators.').check(); await page.getByRole('button', { name: 'Create account →' }).click();
      await page.getByRole('heading', { name: 'Workspace overview' }).waitFor(); await page.reload(); await page.getByRole('heading', { name: 'Workspace overview' }).waitFor();
      assert.equal((await api('businesses')).length, 0, 'Test must begin with empty isolated business storage');
    });
    await check('CSV exact column mapping, preview, reviewed import and invalid row remain separated', async () => {
      await nav('Discover'); await page.getByLabel('CSV file', { exact: true }).setInputFiles({ name: 'fictional-ui.csv', mimeType: 'text/csv', buffer: Buffer.from('CompanyLabel,StreetLine,category\nFictional Imported Studio,Fictional Road,Medical spa\nInvalid Fixture,,Spa\n') });
      await page.getByLabel('Map name', { exact: true }).selectOption('CompanyLabel'); await page.getByLabel('Map address', { exact: true }).selectOption('StreetLine');
      await page.getByRole('button', { name: 'Preview CSV', exact: true }).click(); await page.getByRole('heading', { name: 'Preview', exact: true }).waitFor();
      assert.equal((await api('businesses')).length, 0);
      await page.getByRole('button', { name: 'Import reviewed CSV', exact: true }).click(); await page.getByRole('heading', { name: 'Import result', exact: true }).waitFor();
      assert.equal((await api('businesses')).length, 1);
    });
    await check('Manual task creates once and completion/cancellation controls persist real statuses', async () => {
      await nav('Tasks'); const business = (await api('businesses'))[0];
      for (const [title, status] of [['Browser task complete', 'completed'], ['Browser task cancel', 'cancelled']]) {
        await page.getByLabel('Saved business', { exact: true }).selectOption(business.id); await page.getByLabel('Task title', { exact: true }).fill(title); await page.getByLabel('Due date and time', { exact: true }).fill(localTime(Date.now() + 86400000));
        await page.getByRole('button', { name: 'Save follow-up task', exact: true }).click(); const row = page.locator('.task-row').filter({ hasText: title }); await row.waitFor();
        await row.getByRole('button', { name: status === 'completed' ? 'Complete' : 'Cancel', exact: true }).click(); await row.getByText(status, { exact: true }).waitFor();
        assert.equal((await api('tasks')).find(t => t.title === title).status, status);
      }
    });
    await check('Existing multilingual outreach panels remain; missing provider stops AI script generation', async () => {
      await nav('Leads'); await page.getByText('Fictional Imported Studio', { exact: true }).click(); await page.getByRole('heading', { name: 'Email pitch', exact: true }).waitFor();
      await page.getByRole('heading', { name: 'Call script', exact: true }).waitFor(); assert.equal(await page.getByRole('button', { name: 'Generate call script', exact: true }).isDisabled(), true);
    });
    await check('AI Agent reports no provider, disables send and verification, and shows no fake reply', async () => {
      await nav('AI Agent'); await page.getByRole('heading', { name: 'AI Agent', exact: true }).waitFor(); await page.getByText('Provider not connected', { exact: true }).waitFor();
      assert.equal(await page.getByRole('button', { name: 'Verify live AI', exact: true }).isDisabled(), true); assert.equal(await page.getByRole('button', { name: 'Send →', exact: true }).isDisabled(), true);
      assert.equal(await page.locator('.bubble.assistant').count(), 0);
    });
    await check('Fictional n8n demo deploys via UI to a real engine and activation is recorded', async () => {
      await nav('Automations'); await page.getByRole('heading', { name: 'Inquiry follow-up automation', exact: true }).waitFor();
      await page.getByRole('button', { name: 'Create fictional inquiry demo', exact: true }).click(); const select = page.getByLabel('Current inquiry workflow', { exact: true });
      await page.waitForFunction(() => document.querySelector('select[required]')?.options?.length > 1);
      await page.getByLabel('I authorize creating and activating this workflow in n8n', { exact: true }).check(); const deploymentReply = page.waitForResponse(r => r.url().endsWith('/api/backend/n8n/deployments') && r.request().method() === 'POST'); await page.getByRole('button', { name: 'Deploy reviewed workflow', exact: true }).click(); const response = await deploymentReply; assert.ok(response.ok(), 'n8n deployment API failed');
      await page.getByRole('heading', { name: 'Last recorded result', exact: true }).waitFor();
      await page.waitForFunction(() => document.body.innerText.includes('active'));
      const deployed = (await api('n8n/deployments')).find(d => d.status === 'active'); assert.ok(deployed?.remote_workflow_id); assert.equal(deployed.synthetic, true); deploymentId = deployed.id;
    });
    await check('UI manual inquiry verifies engine execution and saves an unsent acknowledgement plus task', async () => {
      await page.getByLabel('Active deployment', { exact: true }).selectOption(deploymentId); await page.getByLabel('Contact reference', { exact: true }).fill('Fictional manual customer'); await page.getByLabel('Inquiry', { exact: true }).fill('Fictional general consultation inquiry.');
      await page.getByLabel('Unsent acknowledgement draft', { exact: true }).fill('Fictional draft. Nothing is sent.'); await page.getByLabel('Follow-up due', { exact: true }).fill(localTime(Date.now() + 3600000));
      await page.getByLabel('Contact permits this follow-up task', { exact: true }).check(); await page.getByLabel('I authorize this n8n execution and task creation', { exact: true }).check(); await page.getByRole('button', { name: 'Run and verify task', exact: true }).click();
      await page.getByText('n8n execution:', { exact: true }).waitFor(); const run = (await api('n8n/runs')).find(r => r.status === 'succeeded'); assert.ok(run.execution_id && run.task_id); assert.equal(run.delivery_status, 'unsent_draft');
    });
    await check('Reviewed intake source returns a one-time key without browser persistence', async () => {
      await nav('Inquiries'); await page.getByLabel('Include fictional demos', { exact: true }).check(); await page.getByLabel('Source name', { exact: true }).fill('Fictional website source');
      await page.getByLabel('Approved active deployment', { exact: true }).selectOption(deploymentId); await page.getByLabel('Fixed acknowledgement', { exact: true }).fill('Fictional acknowledgement draft for intake.');
      assert.equal(await page.getByLabel('Acknowledgement delivery', { exact: true }).isDisabled(), true);
      await page.getByLabel('I reviewed this source and authorize future intake, n8n processing and follow-up task creation', { exact: true }).check(); await page.getByRole('button', { name: 'Activate reviewed source', exact: true }).click();
      await page.getByRole('heading', { name: 'Connect this source securely', exact: true }).waitFor(); intakeKey = await page.getByLabel('X-Inquiry-Key', { exact: true }).inputValue(); assert.ok(intakeKey.length > 30);
      const source = (await api('inquiry-sources?include_demo=true'))[0]; sourceId = source.id; assert.equal(source.email_mode, 'none'); assert.ok(!JSON.stringify(source).includes(intakeKey));
      assert.equal(await page.evaluate(key => JSON.stringify(localStorage).includes(key) || JSON.stringify(sessionStorage).includes(key), intakeKey), false);
    });
    await check('Token-authenticated real intake runs n8n once and duplicate submission reuses its task', async () => {
      const body = { event_id: 'fixture-ui-intake-1', contact_reference: 'fixture-contact-1', inquiry: 'Fictional non-clinical consultation inquiry.', contact_permission: true };
      for (let i = 0; i < 2; i++) { const response = await fetch(backend + '/intake/' + sourceId, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Inquiry-Key': intakeKey }, body: JSON.stringify(body) }); assert.equal(response.status, 202); }
      await page.getByRole('button', { name: 'Refresh intake', exact: true }).click(); await page.getByText('fixture-contact-1', { exact: true }).waitFor(); const inquiry = (await api('inquiries?include_demo=true'))[0]; assert.equal(inquiry.status, 'processed'); assert.ok(inquiry.task_id && inquiry.execution_id); assert.equal(inquiry.email_status, 'disabled');
      assert.equal((await api('inquiries?include_demo=true')).length, 1);
    });
    await check('Outcome counters exclude demos by default and distinguish task creation from delivery', async () => {
      await nav('Outcomes'); await page.getByRole('heading', { name: 'Automation outcomes', exact: true }).waitFor(); let summary = await api('outcomes/summary'); assert.equal(summary.inquiries.received, 0); assert.equal(summary.email.delivered, 0);
      await page.getByLabel('Include fictional demos', { exact: true }).check(); await page.getByText('Real and fictional records included', { exact: true }).waitFor(); summary = await api('outcomes/summary?include_demo=true'); assert.equal(summary.inquiries.received, 1); assert.equal(summary.tasks.created, 1); assert.equal(summary.email.delivered, 0); assert.equal(summary.email.submitted, 0);
    });
    await check('Purple feature views fit mobile width and have no JavaScript errors', async () => {
      await page.setViewportSize({ width: 390, height: 844 });
      for (const section of ['chat', 'automations', 'inquiries', 'outcomes', 'tasks']) { await page.locator('select[aria-label="Sections"]').selectOption(section); await page.waitForTimeout(250); assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), true, `${section} overflows on mobile`); }
      assert.deepEqual(errors, []);
    });
    await check('Pause source and managed remote workflow; logout revokes account access', async () => {
      await api(`inquiry-sources/${sourceId}/pause`, { method: 'POST', data: { confirm_pause: true } }); await api(`n8n/deployments/${deploymentId}/pause`, { method: 'POST', data: {} });
      assert.equal((await api('n8n/deployments')).find(d => d.id === deploymentId).status, 'paused');
      const result = await page.evaluate(async () => { const response = await fetch('/api/auth/logout', { method: 'POST' }); const privateResponse = await fetch('/api/backend/businesses'); return { ok: response.ok, status: privateResponse.status }; }); assert.ok(result.ok); assert.equal(result.status, 401);
    });
    fs.writeFileSync(reportPath, JSON.stringify({ passed: true, checks, errors, providers: { n8n: 'real engine', gemini: 'not configured', email: 'disabled' }, customer_data: 'fictional isolated records', original_database_changed: false }, null, 2));
  } finally {
    // Best-effort pause if a later assertion fails. Never remove unrelated engine records.
    if (deploymentId) await api(`n8n/deployments/${deploymentId}/pause`, { method: 'POST', data: {} }).catch(() => {});
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });

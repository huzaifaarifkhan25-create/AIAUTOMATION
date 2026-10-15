import asyncio
import hashlib
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

from app.main import create_app
from app.settings import Settings
from backup import backup, restore

CODE = "synthetic-account-workspace-access-code"
PASSWORD = "Synthetic-long-password-2026"


class AccountTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = Settings(database_path=str(self.root / 'accounts.sqlite3'), app_api_token=CODE)
        self.app = create_app(self.settings)
        self.client = self.make_client(self.app)
        await self.app.state.store.put('businesses', 'retained', {'id': 'retained', 'source': 'csv'})

    def make_client(self, app, host='127.0.0.1', base_url='http://testserver'):
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=(host, 1234)), base_url=base_url)
        self.addAsyncCleanup(client.aclose)
        return client

    def body(self, **changes):
        return dict(name='Synthetic Operator', email='operator@example.test', password=PASSWORD,
                    access_code=CODE, confirm_shared_workspace=True, **changes)

    async def signup(self, client=None, body=None):
        response = await (client or self.client).post('/auth/register', json=body or self.body())
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def test_signup_hashes_credentials_and_preserves_existing_records(self):
        result = await self.signup()
        self.assertEqual(result['workspace'], 'shared')
        self.assertEqual(result['user']['email'], 'operator@example.test')
        self.assertNotIn(PASSWORD, str(result)); self.assertNotIn(CODE, str(result))
        self.assertEqual((await self.client.get('/ready')).status_code, 200)
        self.assertEqual(await self.app.state.store.get('businesses', 'retained'), {'id':'retained', 'source':'csv'})
        with sqlite3.connect(self.settings.database_path) as db:
            row = db.execute('SELECT salt,password_hash FROM auth_users').fetchone()
            self.assertNotEqual(row[1], PASSWORD); self.assertEqual(len(row[0]), 32)
            cookie = self.client.cookies.get('aia_session')
            self.assertEqual(db.execute('SELECT token_hash FROM auth_sessions').fetchone()[0], hashlib.sha256(cookie.encode()).hexdigest())

    async def test_register_requires_access_code_and_literal_shared_confirmation(self):
        body = self.body(); body['access_code'] = 'wrong'
        self.assertEqual((await self.client.post('/auth/register', json=body)).status_code, 403)
        for confirmation in (False, 'true', 1):
            body = self.body(); body['confirm_shared_workspace'] = confirmation
            self.assertEqual((await self.client.post('/auth/register', json=body)).status_code, 422)
        self.assertFalse((await self.client.get('/auth/status')).json()['has_accounts'])

    async def test_duplicate_email_normalization_and_generic_login_failure(self):
        body = self.body(); body['email'] = ' OPERATOR@EXAMPLE.TEST '
        await self.signup(body=body)
        self.assertEqual((await self.client.post('/auth/register', json=self.body())).status_code, 409)
        wrong = await self.client.post('/auth/login', json={'email':'operator@example.test','password':'wrong'})
        missing = await self.client.post('/auth/login', json={'email':'missing@example.test','password':'wrong'})
        self.assertEqual(wrong.status_code, 401); self.assertEqual(wrong.json(), missing.json())

    async def test_cookie_mutations_require_csrf_and_reject_other_origins(self):
        result = await self.signup()
        path = '/businesses/retained/tasks'
        body = {'idempotency_key':'auth-task', 'title':'Synthetic account task', 'due_at':'2026-12-01T10:00:00+00:00'}
        self.assertEqual((await self.client.post(path, json=body)).status_code, 403)
        headers = {'X-Workspace-CSRF':result['csrf_token']}
        self.assertEqual((await self.client.post(path, json=body, headers={**headers,'Origin':'https://other.example'})).status_code, 403)
        response = await self.client.post(path, json=body, headers=headers)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual((await self.client.get('/tasks')).json()[0]['title'], body['title'])

    async def test_logout_revokes_session_and_login_rotates_it(self):
        first = await self.signup(); old = self.client.cookies.get('aia_session')
        login = await self.client.post('/auth/login', json={'email':'operator@example.test','password':PASSWORD})
        self.assertEqual(login.status_code, 200)
        other = self.make_client(self.app); other.cookies.set('aia_session', old)
        self.assertEqual((await other.get('/ready')).status_code, 401)
        csrf = login.json()['csrf_token']
        self.assertEqual((await self.client.post('/auth/logout')).status_code, 403)
        current = self.client.cookies.get('aia_session')
        self.assertEqual((await self.client.post('/auth/logout', headers={'X-Workspace-CSRF':csrf})).status_code, 200)
        self.assertEqual((await self.client.get('/ready')).status_code, 401)
        other.cookies.set('aia_session', current)
        self.assertEqual((await other.get('/ready')).status_code, 401)
        self.assertEqual((await other.post('/auth/logout')).status_code, 200)

    async def test_uploaded_collector_and_draft_routes_keep_account_protection(self):
        for path in ('/discovery/collector-status', '/discovery/jobs/missing/spreadsheet.csv',
                     '/ai/businesses/retained/insights'):
            self.assertEqual((await self.client.get(path)).status_code, 401)
        with patch.object(self.app.state.ai, 'chat', new=AsyncMock()) as chat:
            self.assertEqual((await self.client.post('/ai/chat', json={'message':'Show saved leads'})).status_code, 401)
            session = await self.signup()
            self.assertEqual((await self.client.post('/ai/chat', json={'message':'Show saved leads'})).status_code, 403)
            chat.assert_not_awaited()
        self.assertEqual((await self.client.get('/ai/businesses/retained/insights')).json(), [])
        with patch('app.routes.discovery.collector_status', return_value={'ready':False,'code':'browser_missing','message':'Synthetic fixture'}) as status:
            self.assertFalse((await self.client.get('/discovery/collector-status')).json()['ready'])
            status.assert_called_once_with(self.settings.browser_runtime)
        self.assertEqual((await self.client.post('/auth/logout', headers={'X-Workspace-CSRF':session['csrf_token']})).status_code, 200)
        self.assertEqual((await self.client.get('/ai/businesses/retained/insights')).status_code, 401)

    async def test_sessions_and_accounts_survive_restart_and_expire(self):
        await self.signup()
        restarted = self.make_client(create_app(self.settings)); restarted.cookies.update(self.client.cookies)
        self.assertEqual((await restarted.get('/auth/me')).status_code, 200)
        with patch('app.services.auth.time.time', return_value=__import__('time').time() + 43201):
            self.assertEqual((await restarted.get('/auth/me')).status_code, 401)
            self.assertEqual((await restarted.get('/ready')).status_code, 401)
        self.assertEqual((await restarted.post('/auth/login', json={'email':'operator@example.test','password':PASSWORD})).status_code, 200)

    async def test_local_first_account_closes_anonymous_access_and_blocks_remote_signup(self):
        settings = replace(self.settings, app_api_token='')
        app = create_app(settings)
        local, remote = self.make_client(app), self.make_client(app, host='203.0.113.2')
        self.assertEqual((await local.get('/ready')).status_code, 200)
        self.assertFalse((await remote.get('/auth/status')).json()['registration_available'])
        self.assertEqual((await remote.post('/auth/register', json=self.body())).status_code, 403)
        await self.signup(client=local)
        self.assertEqual((await remote.get('/ready')).status_code, 401)
        self.assertEqual((await local.get('/ready')).status_code, 200)

    async def test_production_secure_cookie_and_no_signup_without_invitation(self):
        app = create_app(replace(self.settings, app_env='production', app_allowed_hosts=('app.example.test',)))
        client = self.make_client(app, base_url='https://app.example.test')
        response = await client.post('/auth/register', json=self.body())
        self.assertEqual(response.status_code, 201, response.text)
        cookie = response.headers['set-cookie']
        for attribute in ('__Host-aia_session=', 'HttpOnly', 'Secure', 'SameSite=strict', 'Path=/'):
            self.assertIn(attribute, cookie)
        self.assertEqual((await client.get('/ready')).status_code, 200)
        self.assertFalse((await client.get('/auth/me')).headers.get('access-control-allow-origin'))

    async def test_login_and_registration_origin_rejection(self):
        for path, body in [('/auth/register', self.body()), ('/auth/login', {'email':'operator@example.test','password':PASSWORD})]:
            response = await self.client.post(path, json=body, headers={'Origin':'https://other.example'})
            self.assertEqual(response.status_code, 403)
            response = await self.client.post(path, json=body, headers={'Sec-Fetch-Site':'cross-site'})
            self.assertEqual(response.status_code, 403)

    async def test_rate_limit_persists_across_restart_without_calling_hash_again(self):
        login = {'email':'operator@example.test','password':'wrong'}
        with patch('app.services.auth.password_hash', return_value='dummy'):
            for _ in range(10):
                self.assertEqual((await self.client.post('/auth/login', json=login)).status_code, 401)
            restarted = self.make_client(create_app(self.settings))
            self.assertEqual((await restarted.post('/auth/login', json=login)).status_code, 429)
            with patch('app.services.auth.time.time', return_value=__import__('time').time() + 901):
                self.assertEqual((await restarted.post('/auth/login', json=login)).status_code, 401)

    async def test_validation_never_echoes_passwords_or_access_codes(self):
        body = self.body(); body['password'] = 'secret'; body['access_code'] = 'secretcode' * 100
        response = await self.client.post('/auth/register', json=body)
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(body['password'], response.text); self.assertNotIn(body['access_code'], response.text)
        body = self.body(); body['password'] = ' ' * 12
        self.assertEqual((await self.client.post('/auth/register', json=body)).status_code, 422)

    async def test_bearer_access_and_simultaneous_registration_remain_safe(self):
        one, two = self.make_client(self.app), self.make_client(self.app)
        results = await asyncio.gather(one.post('/auth/register', json=self.body()), two.post('/auth/register', json=self.body()))
        self.assertEqual(sorted(r.status_code for r in results), [201, 409])
        self.assertEqual((await self.client.get('/ready')).status_code, 401)
        self.assertEqual((await self.client.get('/ready', headers={'Authorization':'Bearer '+CODE})).status_code, 200)
        self.assertEqual((await one.get('/ready', headers={'Authorization':'Bearer wrong'})).status_code, 401)

    async def test_backup_restore_preserves_accounts_and_revokes_restored_sessions(self):
        await self.signup()
        folder = backup(Path(self.settings.database_path), self.root / 'scrapes', self.root / 'backups')
        recovered = restore(folder, self.root / 'recovered')
        app = create_app(replace(self.settings, database_path=str(recovered / 'backend.sqlite3')))
        client = self.make_client(app); client.cookies.update(self.client.cookies)
        self.assertEqual((await client.get('/auth/me')).status_code, 401)
        self.assertEqual((await client.post('/auth/login', json={'email':'operator@example.test','password':PASSWORD})).status_code, 200)

    async def test_supabase_accounts_explicitly_unsupported_without_local_fallback(self):
        app = create_app(replace(self.settings, persistence_backend='supabase'))
        client = self.make_client(app)
        self.assertFalse((await client.get('/auth/status')).json()['supported'])
        self.assertEqual((await client.post('/auth/login', json={'email':'operator@example.test','password':PASSWORD})).status_code, 503)

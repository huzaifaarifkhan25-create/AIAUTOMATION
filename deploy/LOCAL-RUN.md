# Windows development launch and private keys

Install Python 3.12 (including the `py` launcher) and Node.js 24 LTS first. Extract
the complete source and preserve your existing `.local` folder when upgrading.
Double-click `START-APP-WINDOWS.bat`: it opens the backend and purple frontend in
separate terminal windows. Wait for both servers, then open
**http://127.0.0.1:3000**. The older UI remains at
http://127.0.0.1:8000/app/. Stop both windows with Ctrl+C when finished.

The launcher installs locked dependencies and keeps servers bound to loopback.
Create your first individual account through Register. Accounts share the same
local workspace; this is not private company separation. If `APP_API_TOKEN` is
configured, registration asks for that private access code.

Provider keys belong in the backend's private runtime. The loopback AI Agent
connection form can hold Gemini for this server session; the local n8n form works
the same way. They do not save cloud secret values. For persistent configuration,
copy root `.env.example` to root `.env`, edit it privately, and use the supported
backend env-file launch described in `WINDOWS-START-HERE.md`. Root `.env` is ignored
by Git. Next.js reads `frontend/.env.local` if you need to override `BACKEND_URL`;
it should normally be `http://127.0.0.1:8000`. Never add provider keys to frontend
environment files. Accounts do not require the former shared preview password.

Get Gemini from [Google AI Studio API keys](https://aistudio.google.com/apikey).
For self-hosted local n8n install Docker Desktop with Linux containers, run
`START-N8N-WINDOWS.bat`, open **http://127.0.0.1:5678**, create the n8n owner, then
Settings → n8n API → Create API key. Use `http://127.0.0.1:5678` as its local base URL.
No n8n Cloud subscription is required. Resend needs a verified sender domain and
actual API/signing keys; follow `PRODUCTION.md` before live delivery.

The batch files are source-reviewed; this cloud is Linux and does not run Windows
batch programs. Docker images and source runtime checks have separate evidence.

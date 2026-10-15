import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from functools import partial

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.database.store import SQLiteStore, SupabaseStore
from app.errors import AppError
from app.routes.businesses import router as businesses_router
from app.routes.csv_import import router as csv_import_router
from app.routes.platform import router as platform_router
from app.routes.discovery import router as discovery_router
from app.routes.execution import router as execution_router
from app.routes.delivery import router as delivery_router
from app.routes.appointments import router as appointments_router
from app.routes.crm import router as crm_router
from app.routes.clients import router as clients_router
from app.routes.dialer import router as dialer_router, callbacks as dialer_callbacks
from app.routes.agent import router as agent_router
from app.routes.ai import router as ai_router
from app.routes.n8n import router as n8n_router
from app.routes.inquiries import router as inquiries_router, public as intake_router
from app.routes.operations import router as operations_router
from app.routes.auth import router as auth_router, same_origin
from app.services.auth import Accounts
from app.services.discovery import Discovery
from app.services.gateway import Gateway
from app.services.platform import Platform
from app.services.execution import Execution
from app.services.appointments import Appointments
from app.services.crm import CRM
from app.services.clients import Clients
from app.services.dialer import Dialer
from app.services.agent import Agent
from app.services.ai import AI
from app.services.n8n import N8N
from app.services.inquiries import Inquiries
from app.settings import Settings
from collect_leads import collect


async def authenticate(request: Request, credentials=Depends(HTTPBearer(auto_error=False))):
    expected = request.app.state.settings.app_api_token
    supplied = credentials.credentials if credentials else ""
    if credentials:
        if expected and secrets.compare_digest(supplied.encode(), expected.encode()):
            return
        raise AppError(401, "unauthorized", "A valid API bearer token is required")
    accounts = request.app.state.accounts
    if request.cookies.get(accounts.cookie):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            same_origin(request)
        await accounts.authorize_cookie(request)
    elif expected or await accounts.has_accounts():
        raise AppError(401, "unauthorized", "A valid API bearer token or account sign-in is required")


def create_app(settings=None, store=None, gateway=None):
    settings = settings or Settings.from_env()
    settings.validate_runtime()
    gateway = gateway or Gateway(settings)
    store = store or (SupabaseStore(settings, gateway) if settings.persistence_backend == "supabase" else SQLiteStore(settings.database_path))
    discovery = Discovery(store, root=Path(settings.scrape_output_path), collector=partial(collect, runtime=settings.browser_runtime))
    platform = Platform(store, gateway)
    execution = Execution(store, platform)
    appointments = Appointments(store, execution)
    execution.appointments = appointments
    crm = CRM(store, platform)
    clients = Clients(store, execution)
    dialer = Dialer(store, platform)
    platform.crm, platform.dialer, platform.execution = crm, dialer, execution
    execution.clients = clients

    @asynccontextmanager
    async def lifespan(app):
        await app.state.agent.recover()
        await app.state.n8n.recover()
        await app.state.inquiries.recover()
        await discovery.recover()
        await appointments.recover()
        await execution.start()
        try:
            yield
        finally:
            await execution.close()
            await discovery.close()

    production = settings.app_env == "production"
    app = FastAPI(title="Med Spa Automation API", version="0.14.0", lifespan=lifespan,
                  docs_url=None if production else "/docs", redoc_url=None if production else "/redoc",
                  openapi_url=None if production else "/openapi.json")
    app.state.settings = settings
    app.state.gateway = gateway
    app.state.store = store
    app.state.accounts = Accounts(settings, store)
    app.state.platform = platform
    app.state.discovery = discovery
    app.state.execution = execution
    app.state.appointments = appointments
    app.state.crm, app.state.clients, app.state.dialer = crm, clients, dialer
    app.state.agent = Agent(app.state)
    app.state.n8n = N8N(app.state)
    app.state.ai = AI(settings, store, platform)
    app.state.inquiries = Inquiries(app.state)
    execution.inquiries = app.state.inquiries

    if settings.app_allowed_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.app_allowed_hosts))

    @app.middleware("http")
    async def response_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-cache" if request.url.path.startswith("/app/") else "no-store"
        if production and request.url.path.startswith("/app/"):
            response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        return response

    @app.exception_handler(AppError)
    async def handle_error(request, error):
        return JSONResponse(status_code=error.status_code, content={"error": {"code": error.code, "message": error.message}},
                            headers={"WWW-Authenticate": "Bearer"} if error.status_code == 401 else None)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        if request.url.path.startswith(("/agent/", "/auth/", "/n8n/", "/inquiry-sources", "/inquiries", "/intake/", "/ai/")):
            return JSONResponse(status_code=422, content={"detail": [
                {"type": e["type"], "loc": list(e["loc"]), "msg": e["msg"]} for e in error.errors()]})
        return await request_validation_exception_handler(request, error)

    @app.get("/health", tags=["Health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def home():
        return RedirectResponse("/app/")

    app.include_router(businesses_router, dependencies=[Depends(authenticate)])
    app.include_router(auth_router)
    app.include_router(csv_import_router, dependencies=[Depends(authenticate)])
    app.include_router(platform_router, dependencies=[Depends(authenticate)])
    app.include_router(discovery_router, dependencies=[Depends(authenticate)])
    app.include_router(execution_router, dependencies=[Depends(authenticate)])
    app.include_router(delivery_router)
    app.include_router(appointments_router, dependencies=[Depends(authenticate)])
    app.include_router(crm_router, dependencies=[Depends(authenticate)])
    app.include_router(clients_router, dependencies=[Depends(authenticate)])
    app.include_router(dialer_router, dependencies=[Depends(authenticate)])
    app.include_router(operations_router, dependencies=[Depends(authenticate)])
    app.include_router(agent_router, dependencies=[Depends(authenticate)])
    app.include_router(ai_router, dependencies=[Depends(authenticate)])
    app.include_router(n8n_router, dependencies=[Depends(authenticate)])
    app.include_router(inquiries_router, dependencies=[Depends(authenticate)])
    app.include_router(intake_router)
    app.include_router(dialer_callbacks)
    app.mount("/app", StaticFiles(directory=Path(__file__).with_name("static"), html=True), name="workspace")
    return app


app = create_app()

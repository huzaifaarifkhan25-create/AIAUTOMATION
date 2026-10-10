import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from functools import partial

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
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
from app.routes.operations import router as operations_router
from app.routes.ai import router as ai_router
from app.services.discovery import Discovery
from app.services.gateway import Gateway
from app.services.platform import Platform
from app.services.execution import Execution
from app.services.appointments import Appointments
from app.services.crm import CRM
from app.services.clients import Clients
from app.services.dialer import Dialer
from app.services.ai import AI
from app.settings import Settings
from collect_leads import collect


async def authenticate(request: Request, credentials=Depends(HTTPBearer(auto_error=False))):
    expected = request.app.state.settings.app_api_token
    if expected:
        supplied = credentials.credentials if credentials else ""
        if not secrets.compare_digest(supplied.encode(), expected.encode()):
            raise AppError(401, "unauthorized", "A valid API bearer token is required")


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
        await discovery.recover()
        await appointments.recover()
        await execution.start()
        try:
            yield
        finally:
            await execution.close()
            await discovery.close()

    production = settings.app_env == "production"
    app = FastAPI(title="Med Spa Automation API", version="0.10.0", lifespan=lifespan,
                  docs_url=None if production else "/docs", redoc_url=None if production else "/redoc",
                  openapi_url=None if production else "/openapi.json")
    app.state.settings = settings
    app.state.gateway = gateway
    app.state.store = store
    app.state.platform = platform
    app.state.discovery = discovery
    app.state.execution = execution
    app.state.appointments = appointments
    app.state.crm, app.state.clients, app.state.dialer = crm, clients, dialer
    app.state.ai = AI(settings, store, platform)

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

    @app.get("/health", tags=["Health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def home():
        return RedirectResponse("/app/")

    app.include_router(businesses_router, dependencies=[Depends(authenticate)])
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
    app.include_router(ai_router, dependencies=[Depends(authenticate)])
    app.include_router(dialer_callbacks)
    app.mount("/app", StaticFiles(directory=Path(__file__).with_name("static"), html=True), name="workspace")
    return app


app = create_app()

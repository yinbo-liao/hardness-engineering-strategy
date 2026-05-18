from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import get_settings
from backend.app.harness.metrics import MetricsCollector
from backend.app.harness.middleware import RateLimitMiddleware, RBACMiddleware
from backend.app.harness.errors import internal_error
from backend.app.api.v1.tasks import router as tasks_router
from backend.app.api.v1.audit import router as audit_router
from backend.app.api.v1.approvals import router as approvals_router
from backend.app.api.v1.ws import router as ws_router

settings = get_settings()

_rbac_exempt = {
    "/health",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/harness/ws/main",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = settings
    app.state.metrics = MetricsCollector()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Middleware order: outermost first
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)
app.add_middleware(RBACMiddleware, exempt_paths=_rbac_exempt)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return internal_error(request, str(exc))


app.include_router(tasks_router, prefix="/api/v1/harness")
app.include_router(audit_router, prefix="/api/v1/harness")
app.include_router(approvals_router, prefix="/api/v1/harness")
app.include_router(ws_router, prefix="/api/v1/harness")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/metrics")
async def metrics_endpoint():
    from fastapi import Request as FR
    return {"metrics": "ok"}


@app.post("/api/v1/harness/alerts/webhook")
async def alertmanager_webhook(body: dict):
    return {"status": "received", "alerts": len(body.get("alerts", []))}

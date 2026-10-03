import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.api.dashboard import router as dashboard_router
from app.api.transactions import router as transactions_router
from app.api.alerts import router as alerts_router
from app.api.audit_logs import router as audit_logs_router
from app.api.graph import router as graph_router
from app.api.labels import router as labels_router
from app.api.cross_border import router as cross_border_router
from app.api.ml import router as ml_router
from app.api.auth import router as auth_router
from app.api.merchants import router as merchants_router
from app.api.orders import router as orders_router
from app.api.payments import router as payments_router
from app.api.demo_qris import router as demo_qris_router
from app.api.federated import router as federated_router
from app.api.reports import router as reports_router
from app.api.health import router as health_router
from app.api.admin import router as admin_router
from app.api.public import router as public_router


logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("fingraph.request")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    description="FinGraph QRIS API untuk keamanan transaksi UMKM. Integrasi PJP pada Mode Demo bersifat simulasi.",
    docs_url="/docs" if settings.ENABLE_API_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_API_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_API_DOCS else None,
    debug=settings.DEBUG,
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - started) * 1000,
    )
    return response


@app.get("/")
def root():
    return {
        "message": "FinGraph QRIS API is running",
        "status": "ok",
        "version": settings.API_VERSION,
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "fingraph-qris-backend",
        "demo_mode": settings.demo_mode,
    }


@app.get("/api/v1/health")
def api_health_check():
    return health_check()


app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(transactions_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(audit_logs_router, prefix="/api/v1")
app.include_router(graph_router, prefix="/api/v1")
app.include_router(labels_router, prefix="/api/v1")
app.include_router(cross_border_router, prefix="/api/v1")
app.include_router(ml_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(merchants_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
if settings.demo_mode and settings.ENABLE_DEMO_ENDPOINTS:
    app.include_router(demo_qris_router, prefix="/api/v1")
app.include_router(federated_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/v1")

logger.info(
    "startup app_env=%s demo_mode=%s docs=%s database_host=%s neo4j_required=%s artifact_dir=%s",
    settings.APP_ENV,
    settings.demo_mode,
    settings.ENABLE_API_DOCS,
    settings.database_host,
    settings.NEO4J_REQUIRED,
    settings.ML_ARTIFACT_DIR,
)

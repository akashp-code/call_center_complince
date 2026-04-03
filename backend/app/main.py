from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.api.v1.routes import router

settings = get_settings()
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_startup", env=settings.APP_ENV)
    yield
    logger.info("app_shutdown")


app = FastAPI(
    title="Call Center Compliance API",
    description=(
        "AI-powered call center compliance analysis. "
        "Accepts Base64-encoded MP3 recordings and returns structured compliance metrics."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=str(request.url), error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "An unexpected error occurred.", "detail": str(exc)},
    )


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(router, prefix="/api")


# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": "Call Center Compliance API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }

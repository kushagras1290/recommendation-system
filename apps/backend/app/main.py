from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from sqlalchemy.exc import OperationalError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.config import get_settings
from app.core.exceptions import (
    NotFoundError,
    RecSysError,
    TrainingError,
    ValidationError as RecSysValidationError,
)
from app.core.logging_config import configure_logging
from app.db.database import init_db
from app.db.seed import seed_if_empty
from app.api import events, evaluations, experiments, health, models_api, recommendations

settings = get_settings()
configure_logging(settings.log_level)
logger = structlog.get_logger(__name__)


_DB_INIT_MAX_ATTEMPTS = 6
_DB_INIT_BASE_WAIT = 5  # seconds; doubles each attempt → 5, 10, 20, 40, 80


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", app=settings.app_name, debug=settings.debug)
    for attempt in range(1, _DB_INIT_MAX_ATTEMPTS + 1):
        try:
            init_db()
            break
        except OperationalError as exc:
            if attempt == _DB_INIT_MAX_ATTEMPTS:
                logger.error(
                    "db_init_failed",
                    attempts=_DB_INIT_MAX_ATTEMPTS,
                    error=str(exc),
                )
                raise
            wait = _DB_INIT_BASE_WAIT * (2 ** (attempt - 1))
            logger.warning(
                "db_init_retry",
                attempt=attempt,
                wait_seconds=wait,
                error=str(exc),
            )
            await asyncio.sleep(wait)
    seed_if_empty()
    yield
    logger.info("shutdown")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="End-to-End Recommendation System API — candidate generation, ranking, evaluation, and A/B testing.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(NotFoundError)
async def _not_found(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={
        "success": False,
        "error": {"code": "NOT_FOUND", "message": str(exc)},
        "request_id": getattr(request.state, "request_id", None),
    })


@app.exception_handler(RecSysValidationError)
async def _validation(request: Request, exc: RecSysValidationError):
    return JSONResponse(status_code=422, content={
        "success": False,
        "error": {"code": "VALIDATION_ERROR", "message": str(exc)},
        "request_id": getattr(request.state, "request_id", None),
    })


@app.exception_handler(TrainingError)
async def _training(request: Request, exc: TrainingError):
    return JSONResponse(status_code=400, content={
        "success": False,
        "error": {"code": "TRAINING_ERROR", "message": str(exc)},
        "request_id": getattr(request.state, "request_id", None),
    })


@app.exception_handler(RecSysError)
async def _recsys(request: Request, exc: RecSysError):
    logger.error("recsys_error", error=str(exc))
    return JSONResponse(status_code=500, content={
        "success": False,
        "error": {"code": "INTERNAL_ERROR", "message": "An internal error occurred"},
        "request_id": getattr(request.state, "request_id", None),
    })


@app.exception_handler(PydanticValidationError)
async def _pydantic(request: Request, exc: PydanticValidationError):
    return JSONResponse(status_code=422, content={
        "success": False,
        "error": {"code": "VALIDATION_ERROR", "message": str(exc.errors()[0]["msg"])},
        "request_id": getattr(request.state, "request_id", None),
    })


app.include_router(health.router, tags=["system"])
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
app.include_router(models_api.router, prefix="/models", tags=["models"])
app.include_router(evaluations.router, prefix="/evaluations", tags=["evaluations"])
app.include_router(experiments.router, prefix="/experiments", tags=["experiments"])

from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.throttle import limiter
from app.infrastructure.database.seed import seed_initial_users
from app.infrastructure.database.session import engine
from app.infrastructure.services.security.password_hasher_impl import (
    Argon2PasswordHasher,
)
from app.infrastructure.utils.logging import configure_logging
from app.presentation.common.dependencies import get_uow
from app.presentation.common.errors.handlers import app_exception_handler
from app.presentation.common.trace_id import TraceIDMiddleware
from app.presentation.graphql.router import graphql_app
from app.utils.app_exception import AppException


@asynccontextmanager
async def lifespan(_app: FastAPI):
    uow = get_uow()
    password_hasher = Argon2PasswordHasher()
    await seed_initial_users(uow=uow, password_hasher=password_hasher)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="FastAPI Core GraphQL",
    version=settings.APP_VERSION,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.get("/health")
async def health():
    timestamp = datetime.now(UTC).isoformat()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "ok",
            "timestamp": timestamp,
        }
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "database": "unavailable",
                "timestamp": timestamp,
            },
        )


app.add_middleware(TraceIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppException, app_exception_handler)

app.include_router(graphql_app, prefix="/graphql")

configure_logging()

"""FastAPI application factory and ASGI entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import init_components, shutdown_components
from app.api.routes import router
from app.core.config import get_settings
from app.errors.exceptions import RoverError
from app.errors.handlers import rover_error_handler, unhandled_error_handler
from app.observability.logging_config import configure_logging
from app.observability.middleware import RequestContextMiddleware
from app.security.auth import ApiKeyAuthenticator
from app.security.middleware import SecurityMiddleware
from app.security.rate_limit import TokenBucketRateLimiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build components on startup, close them on shutdown."""
    init_components()
    yield
    await shutdown_components()


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="CrowdCompass Rover",
        version="1.1.0",
        description="Multilingual semantic search agent for World Cup host cities.",
        lifespan=lifespan,
    )

    # Exception handlers (problem+json).
    app.add_exception_handler(RoverError, rover_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    # Middleware stack (outermost first): context -> security -> CORS -> app.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        SecurityMiddleware,
        authenticator=ApiKeyAuthenticator(settings.api_key_set),
        limiter=TokenBucketRateLimiter(
            rate=settings.rate_limit_rate, capacity=settings.rate_limit_capacity
        ),
    )
    app.add_middleware(RequestContextMiddleware)

    app.include_router(router, prefix="/api")
    return app


app = create_app()

"""build FastAPI applications for the Lab 2 service entry points."""

from collections.abc import Iterable
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.mongo import close_mongo_client


LAB1_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def create_service_app(
    service_name: str,
    routers: Iterable[APIRouter],
) -> FastAPI:
    """create one service app without changing the Lab 1 monolith."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        """close optional shared clients when the service stops."""

        try:
            yield
        finally:
            close_mongo_client()

    app = FastAPI(
        title=f"Handshake {service_name}",
        description="Pair 16 Handshake Lab 2 service",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=LAB1_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in routers:
        app.include_router(router)

    @app.get("/health")
    def health_check() -> dict[str, str]:
        """return a service-specific liveness response."""

        return {
            "status": "healthy",
            "service": service_name,
        }

    return app

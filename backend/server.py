from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.exceptions import (
    AfscResolutionError,
    AfscValidationError,
    DomainError,
    RosterImportError,
    RosterNotFoundError,
)
from app.routes import router


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title="Paratus AFSC Roster API")
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if not origins:
        origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _register_exception_handlers(application)
    application.include_router(router)
    return application


def _register_exception_handlers(application: FastAPI) -> None:
    async def _client_error(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    for exc_type in (AfscValidationError, AfscResolutionError, RosterImportError):
        application.add_exception_handler(exc_type, _client_error)

    @application.exception_handler(RosterNotFoundError)
    async def _not_found(request: Request, exc: RosterNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @application.exception_handler(DomainError)
    async def _domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})


app = create_app()


if __name__ == "__main__":
    import os

    import uvicorn

    host = os.environ.get("HOST", "127.0.0.1")
    reload = os.environ.get("RELOAD", "true").lower() in {"1", "true", "yes"}
    uvicorn.run("server:app", host=host, port=8000, reload=reload)

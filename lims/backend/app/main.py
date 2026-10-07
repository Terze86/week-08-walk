import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app import models  # noqa: F401  (register all tables)
from app.core.audit import request_id_var
from app.core.config import get_settings
from app.core.errors import DomainError
from app.modules.admin.router import router as admin_router
from app.modules.cases.router import router as cases_router
from app.modules.custody.router import router as custody_router
from app.modules.identity.router import router as identity_router
from app.modules.receipt.router import router as receipt_router
from app.modules.reference.router import router as reference_router
from app.modules.work.router import router as work_router


def create_app() -> FastAPI:
    settings = get_settings()  # fail fast on invalid production configuration
    app = FastAPI(title="Forensic DNA LIMS", version="0.1.0")

    @app.middleware("http")
    async def request_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_var.set(rid[:64])
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid[:64]
        return response

    @app.exception_handler(DomainError)
    async def domain_error(_: Request, exc: DomainError) -> JSONResponse:
        body: dict[str, object] = {"code": exc.code, "message": exc.message}
        if exc.rule:
            body["rule"] = exc.rule
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment.value}

    api_prefix = "/api"
    app.include_router(identity_router, prefix=api_prefix)
    app.include_router(admin_router, prefix=api_prefix)
    app.include_router(reference_router, prefix=api_prefix)
    app.include_router(cases_router, prefix=api_prefix)
    app.include_router(receipt_router, prefix=api_prefix)
    app.include_router(custody_router, prefix=api_prefix)
    app.include_router(work_router, prefix=api_prefix)
    return app


app = create_app()

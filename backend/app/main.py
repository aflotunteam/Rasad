import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import router as v1_router
from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.responses import fail

log = logging.getLogger("rasad")
settings = get_settings()

app = FastAPI(
    title="RASAD API",
    version="0.1.0",
    description="Iqtisodiy xavf signallarini tahlil qilish va ekspert qarorini qo‘llab-quvvatlash platformasi. "
    "Namoyish ma’lumotlari sintetik.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.exception_handler(AppError)
async def _app_error(_: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content=fail(exc.code, exc.message, exc.details))


@app.exception_handler(RequestValidationError)
async def _validation_error(_: Request, exc: RequestValidationError):
    details = [
        {"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=fail(ErrorCode.DATA_VALIDATION, "Kiritilgan ma’lumotlar noto‘g‘ri", details),
    )


@app.exception_handler(StarletteHTTPException)
async def _http_error(_: Request, exc: StarletteHTTPException):
    code = ErrorCode.DATA_NOT_FOUND if exc.status_code == 404 else ErrorCode.SYSTEM
    message = "Manzil topilmadi" if exc.status_code == 404 else str(exc.detail)
    return JSONResponse(status_code=exc.status_code, content=fail(code, message))


@app.exception_handler(Exception)
async def _unhandled(_: Request, exc: Exception):
    log.exception("Kutilmagan xato", exc_info=exc)
    return JSONResponse(status_code=500, content=fail(ErrorCode.SYSTEM, "Server xatosi"))


app.include_router(v1_router, prefix=settings.api_prefix)

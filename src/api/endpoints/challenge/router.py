# -*- coding: utf-8 -*-

from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import APIRouter, HTTPException, Request, Depends, Query, Body

from api.core.constants import ErrorCodeEnum, ALPHANUM_HYPHEN_REGEX
from api.core.schemas import BaseResPM
from api.core.responses import BaseResponse
from api.core.exceptions import BaseHTTPException
from api.core.dependencies.auth import auth_api_key
from api.logger import logger

from . import service
from .schemas import Fingerprinter, BuildAndRunRequest


router = APIRouter(tags=["Challenge"])


@router.get(
    "/health",
    summary="Health check",
    description="Check if the VM runner service is healthy and running.",
    response_class=JSONResponse,
)
def get_health(request: Request):
    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Health check...")

    return {
        "status": "healthy",
        "service": "vm-runner",
        "message": "VM runner is up and running"
    }


@router.post(
    "/build_and_run",
    summary="Build and run bot container",
    description="Receives bot.py and Dockerfile, builds Docker container, and runs the bot.",
    response_class=JSONResponse,
    responses={422: {}, 500: {}},
)
def post_build_and_run(request: Request, payload: BuildAndRunRequest):
    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Building and running bot container...")

    try:
        result = service.build_and_run_bot(
            bot_py=payload.bot_py,
            dockerfile=payload.dockerfile,
            session_count=payload.session_count,
        )
        logger.success(f"[{_request_id}] - Successfully built and ran bot container.")
        return result
    except HTTPException:
        raise
    except Exception as err:
        logger.exception(f"[{_request_id}] - Failed to build and run bot container!")
        # Truncate error message to avoid Pydantic validation error (max 256 chars)
        error_msg = str(err)
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "... (truncated)"
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.INTERNAL_SERVER_ERROR,
            message=f"Failed to build/run bot: {error_msg}",
        )


@router.post(
    "/_fp-js",
    summary="Save miner fingerprinter",
    description="This endpoint retrieves the miner fingerprinter from the challenger container.",
    response_model=BaseResPM,
    responses={401: {}, 422: {}},
    dependencies=[Depends(auth_api_key)],
)
def post_fingerprinter(request: Request, fingerprinter: Fingerprinter):

    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Saving miner fingerprinter...")
    try:
        service.save_fingerprinter(fingerprinter=fingerprinter)
        logger.success(f"[{_request_id}] - Successfully saved miner fingerprinter.")
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"[{_request_id}] - Failed to save miner fingerprinter!")
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.INTERNAL_SERVER_ERROR,
            message="Failed to save miner fingerprinter!",
        )

    _response = BaseResponse(
        request=request,
        message="Successfully saved miner fingerprinter.",
    )
    return _response








__all__ = [
    "router",
]

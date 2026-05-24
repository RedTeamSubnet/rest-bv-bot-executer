# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field, field_validator

_fingerprinter_js_content = """(function(){const e=new URLSearchParams(window.location.search).get("order_id"),n={userAgent:navigator.userAgent},t={fingerprint:btoa(JSON.stringify(n)).slice(0,32),timestamp:(new Date).toISOString(),order_id:e};fetch(window.FINGERPRINT_ENDPOINT,{method:"POST",body:JSON.stringify(t),headers:{"Content-Type":"application/json","Accept":"application/json"}}).then(e=>e.ok?e.json():Promise.reject(new Error(`HTTP error! status: ${e.status}`))).catch(e=>console.error("Error sending fingerprint:",e));})();"""


class Fingerprinter(BaseModel):
    fingerprinter_js: str = Field(
        title="fingerprinter.js",
        min_length=2,
        description="System-provided fingerprinter.js script for fingerprint detection.",
        examples=[_fingerprinter_js_content],
    )

    @field_validator("fingerprinter_js", mode="after")
    @classmethod
    def _check_fingerprinter_js_lines(cls, val: str) -> str:
        _lines = val.split("\n")
        if len(_lines) > 1000:
            raise ValueError(
                "fingerprinter_js content is too long, max 1000 lines are allowed!"
            )
        return val


class BuildAndRunRequest(BaseModel):
    bot_py: str = Field(
        ...,
        title="bot.py",
        min_length=2,
        description="The bot.py source code to be executed.",
    )
    dockerfile: str = Field(
        ...,
        title="Dockerfile",
        min_length=2,
        description="Dockerfile content for building the bot container.",
    )
    session_count: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Number of sessions to run the bot.",
    )
    score_job_id: str = Field(
        default="",
        max_length=128,
        description=(
            "Optional caller-supplied job ID. When set the bot container is named "
            "bot_container_<id> and tagged with docker label score_job_id=<id> so "
            "callers can locate and stream its logs."
        ),
    )

    @field_validator("bot_py", mode="after")
    @classmethod
    def _check_bot_py_lines(cls, val: str) -> str:
        _lines = val.split("\n")
        if len(_lines) > 2000:
            raise ValueError("bot_py content is too long, max 2000 lines are allowed!")
        return val

    @field_validator("dockerfile", mode="after")
    @classmethod
    def _check_dockerfile_lines(cls, val: str) -> str:
        _lines = val.split("\n")
        if len(_lines) > 500:
            raise ValueError("dockerfile content is too long, max 500 lines are allowed!")
        return val


__all__ = ["Fingerprinter", "BuildAndRunRequest"]

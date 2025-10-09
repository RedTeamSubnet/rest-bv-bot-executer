# -*- coding: utf-8 -*-

from pydantic import Field, SecretStr, AnyHttpUrl, IPvAnyAddress
from pydantic_settings import SettingsConfigDict

from api.core.constants import ENV_PREFIX
from ._base import FrozenBaseConfig


class ChallengeConfig(FrozenBaseConfig):
    base_url: AnyHttpUrl = Field(...)
    model_config = SettingsConfigDict(env_prefix=f"{ENV_PREFIX}CHALLENGE_")


__all__ = [
    "ChallengeConfig",
]

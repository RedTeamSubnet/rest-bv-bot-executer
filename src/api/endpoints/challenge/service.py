# -*- coding: utf-8 -*-

import os
import uuid
from typing import Dict
from urllib.parse import quote

import docker

from api.config import config
from api.logger import logger

from ._utils import (
    build_bot_environment,
    ensure_phase_network,
    get_bot_network_gateway,
    log_build_event,
    poll_simple_bot_result,
    run_miner_container,
    write_build_context,
)


def build_bot_image(bot_py: str, dockerfile: str, score_job_id: str = "") -> Dict:
    logger.info("Starting miner image build...")
    write_build_context(bot_py=bot_py, dockerfile=dockerfile)
    docker_client = docker.from_env()
    try:
        _, build_logs = docker_client.images.build(
            path=config.challenge.commit_dir,
            dockerfile="bot/Dockerfile",
            tag=config.challenge.miner_image_tag,
            rm=True,
        )
        for log in build_logs:
            log_build_event(log)
        logger.success(
            f"Successfully built miner image: {config.challenge.miner_image_tag}"
        )
        return {
            "status": "success",
            "message": "Miner image built successfully",
            "image_tag": config.challenge.miner_image_tag,
            "score_job_id": score_job_id,
        }
    except docker.errors.BuildError as err:
        logger.error(f"Docker build error: {err}")
        for log in getattr(err, "build_log", []) or []:
            if isinstance(log, dict):
                log_build_event(log)
            else:
                logger.error(f"Build: {log}")
        raise ValueError(f"Failed to build Docker image: {str(err)}")


def run_simple_bot(score_job_id: str = "", timeout_sec: int = 60) -> Dict:
    docker_client = docker.from_env()
    user_identifier = score_job_id or uuid.uuid4().hex
    public_url = str(config.challenge.simple_bot_url).rstrip("/")
    frontend_url = public_url
    simple_web_url = f"{frontend_url}?user_identifier={quote(user_identifier)}"
    network_name = ensure_phase_network(
        docker_client,
        config.challenge.simple_bot_network_name,
        internal=False,
    )
    container_name = "bot_container"
    labels = {"type": "bot-executor-simple"}
    if score_job_id:
        labels["score_job_id"] = score_job_id

    env = build_bot_environment(score_job_id)
    env.update(
        {
            "CHALLENGE_BASE_URL": frontend_url,
            "CHALLENGE_WEB_URL": simple_web_url,
            "SIMPLE_BOT_USER_IDENTIFIER": user_identifier,
        }
    )
    logger.info(f"Running miner image against simple bot page: {simple_web_url}")
    runner_error = ""
    try:
        run_miner_container(
            docker_client=docker_client,
            image_tag=config.challenge.miner_image_tag,
            container_name=container_name,
            labels=labels,
            environment=env,
            network_name=network_name,
        )
    except Exception as err:
        runner_error = str(err)
        logger.warning(f"Simple bot miner container exited unsuccessfully: {err}")
        return {
            "status": "success",
            "passed": False,
            "is_bot": True,
            "user_identifier": user_identifier,
            "runner_error": runner_error,
        }
    is_bot = poll_simple_bot_result(
        user_identifier, timeout_sec=timeout_sec, result_url=public_url
    )
    passed = is_bot is False
    return {
        "status": "success",
        "passed": passed,
        "is_bot": is_bot,
        "user_identifier": user_identifier,
        "runner_error": runner_error,
    }


def run_web_bot(session_count: int = 2, score_job_id: str = "") -> Dict:
    docker_client = docker.from_env()
    network_name = ensure_phase_network(
        docker_client,
        config.challenge.challenge_network_name,
        internal=True,
    )
    gateway = get_bot_network_gateway(docker_client, network_name)
    challenge_https_port = os.getenv("CHALLENGE_HTTPS_PROXY_PORT", "10443")
    challenge_base_url = f"https://{gateway}:{challenge_https_port}"
    challenge_web_url = f"{challenge_base_url}/_web"
    container_name = "bot_container"
    labels = {"type": "bot-executor-run"}
    if score_job_id:
        labels["score_job_id"] = score_job_id

    env = build_bot_environment(score_job_id)
    env.update(
        {
            "CHALLENGE_BASE_URL": challenge_base_url,
            "CHALLENGE_WEB_URL": challenge_web_url,
            "BV_SESSION_COUNT": session_count,
        }
    )
    logger.info(f"Running miner image against challenge page: {challenge_web_url}")
    run_miner_container(
        docker_client=docker_client,
        image_tag=config.challenge.miner_image_tag,
        container_name=container_name,
        labels=labels,
        environment=env,
        network_name=network_name,
    )
    return {
        "status": "success",
        "message": "Bot executed successfully",
        "sessions_completed": session_count,
    }


__all__ = [
    "ensure_phase_network",
    "get_bot_network_gateway",
    "build_bot_image",
    "run_simple_bot",
    "run_web_bot",
]

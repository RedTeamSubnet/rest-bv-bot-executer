# -*- coding: utf-8 -*-

import os
import shutil
import time
from typing import Dict

import docker
import requests
from pydantic import validate_call

from api.config import config
from api.logger import logger


def decode_bytes(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.decode("utf-8", errors="replace")


def log_multiline(prefix: str, output: str, level: str = "debug") -> None:
    if not output:
        return
    log_fn = getattr(logger, level)
    for line in output.splitlines():
        line = line.rstrip()
        if line:
            log_fn(f"{prefix}: {line}")


def log_build_event(event: Dict) -> None:
    if "stream" in event:
        log_multiline("Build", str(event["stream"]), "debug")
    if "status" in event:
        detail = event.get("progress") or event.get("id") or ""
        logger.debug(f"Build: {event['status']} {detail}".rstrip())
    if "aux" in event:
        logger.debug(f"Build aux: {event['aux']}")
    if "errorDetail" in event:
        logger.error(f"Build error detail: {event['errorDetail']}")
    elif "error" in event:
        logger.error(f"Build error: {event['error']}")


def _reset_build_context(commit_dir: str) -> str:
    bot_dir = os.path.join(commit_dir, "bot")
    if os.path.isdir(bot_dir):
        shutil.rmtree(bot_dir)
    os.makedirs(bot_dir, exist_ok=True)
    return bot_dir


def write_build_context(bot_py: str, dockerfile: str) -> None:
    bot_dir = _reset_build_context(config.challenge.commit_dir)
    with open(os.path.join(bot_dir, "bot.py"), "w") as f:
        f.write(bot_py)
    with open(os.path.join(bot_dir, "Dockerfile"), "w") as f:
        f.write(dockerfile)


@validate_call(config={"arbitrary_types_allowed": True})
def ensure_phase_network(
    docker_client: docker.DockerClient, network_name: str, internal: bool
) -> str:
    """Ensure a phase-specific inner network exists in DinD."""
    try:
        docker_client.networks.get(network_name)
        logger.info(
            f"Bot network '{network_name}' already exists, using existing network"
        )
        return network_name
    except docker.errors.NotFound:
        logger.info(f"Bot network '{network_name}' not found, creating it...")

    try:
        docker_client.networks.create(
            name=network_name,
            driver="bridge",
            internal=internal,
            check_duplicate=True,
            labels={"type": "bot-executor", "phase": network_name},
        )
        logger.success(f"Bot network '{network_name}' created successfully")
    except docker.errors.APIError as err:
        if "already exists" not in str(err).lower():
            raise
        logger.info(
            f"Bot network '{network_name}' already exists (created concurrently)"
        )
    return network_name


@validate_call(config={"arbitrary_types_allowed": True})
def get_bot_network_gateway(
    docker_client: docker.DockerClient, network_name: str
) -> str:
    """Return bridge gateway address reachable by bot containers."""
    network = docker_client.networks.get(network_name)
    for network_config in network.attrs.get("IPAM", {}).get("Config", []):
        gateway = network_config.get("Gateway")
        if gateway:
            return gateway
    raise ValueError(f"Could not determine gateway for bot network '{network_name}'")


def run_miner_container(
    *,
    docker_client: docker.DockerClient,
    image_tag: str,
    container_name: str,
    labels: Dict[str, str],
    environment: Dict[str, str | int],
    network_name: str,
) -> str:
    docker_transport_errors = (
        docker.errors.APIError,
        requests.exceptions.RequestException,
    )

    def force_remove(container_to_remove: docker.models.containers.Container) -> None:
        try:
            container_to_remove.remove(force=True)
            logger.info(f"Removed bot container: {container_name}")
        except docker.errors.NotFound:
            pass
        except docker_transport_errors as err:
            logger.warning(f"Could not remove bot container {container_name}: {err}")

    def remove_existing_container() -> None:
        try:
            existing = docker_client.containers.get(container_name)
        except docker.errors.NotFound:
            return
        except docker_transport_errors as err:
            logger.warning(f"Could not inspect bot container {container_name}: {err}")
            return

        logger.warning(
            f"Container name is already allocated: {container_name}; "
            "waiting for the previous run"
        )
        try:
            if existing.status == "running":
                existing.wait(timeout=config.challenge.container_run_timeout_sec)
        except docker.errors.NotFound:
            return
        except docker_transport_errors as err:
            logger.warning(
                f"Previous bot container could not be waited on; "
                f"force-removing it: {err}"
            )
        force_remove(existing)

    container = None
    try:
        runner_path = os.path.abspath(
            os.path.join(config.challenge.commit_dir, "bot_runner.py")
        )
        logger.info(f"Runner path: {runner_path}")
        run_kwargs = {
            "name": container_name,
            "labels": labels,
            "environment": environment,
            "network": network_name,
            "tmpfs": {
                "/tmp": "size=512M,mode=1777",
                "/dev/shm": "size=2g",
                "/var/tmp": "size=256M,mode=1777",
            },
            "mem_limit": "8g",
            "memswap_limit": "8g",
            "cpu_quota": 100000,
            "pids_limit": 256,
            "cap_drop": ["NET_RAW", "NET_ADMIN"],
            "security_opt": ["no-new-privileges"],
            "detach": True,
            "auto_remove": False,
            "shm_size": "4g",
            "read_only": False,
            "entrypoint": ["python3"],
            "command": ["/app/bot_runner.py"],
            "volumes": {runner_path: {"bind": "/app/bot_runner.py", "mode": "ro"}},
        }
        remove_existing_container()
        for attempt in range(3):
            try:
                container = docker_client.containers.run(image_tag, **run_kwargs)
                break
            except docker.errors.APIError as exc:
                if container is not None:
                    force_remove(container)
                    container = None
                if "already in use" not in str(exc).lower() or attempt == 2:
                    raise
                remove_existing_container()
        if container is None:
            raise RuntimeError(f"Could not start bot container '{container_name}'")
        try:
            wait_result = container.wait(
                timeout=config.challenge.container_max_runtime_sec
            )
        except requests.exceptions.Timeout as err:
            logger.warning(
                f"Bot container {container_name} exceeded "
                f"{config.challenge.container_max_runtime_sec}s; removing it"
            )
            force_remove(container)
            raise TimeoutError(
                f"Bot container '{container_name}' exceeded maximum runtime of "
                f"{config.challenge.container_max_runtime_sec}s"
            ) from err
        except docker.errors.NotFound as err:
            raise RuntimeError(
                f"Bot container '{container_name}' disappeared before completion"
            ) from err
        except docker_transport_errors as err:
            force_remove(container)
            raise RuntimeError(
                f"Could not wait for bot container '{container_name}': {err}"
            ) from err
        exit_code = (
            int(wait_result.get("StatusCode", 1))
            if isinstance(wait_result, dict)
            else 0
        )
        try:
            bot_logs = decode_bytes(container.logs(stdout=True, stderr=True))
        except docker.errors.NotFound:
            bot_logs = ""
        log_multiline(f"Bot {container_name}", bot_logs, "debug")
        if exit_code != 0:
            log_multiline(f"Bot {container_name} failed", bot_logs, "info")
            raise ValueError(
                f"Bot container '{container_name}' exited with status {exit_code}"
            )
        return bot_logs
    finally:
        if container is not None:
            logger.debug(f"Bot container finished: {container_name}")
            force_remove(container)


def build_bot_environment(score_job_id: str) -> Dict[str, str]:
    return {
        "SCORE_JOB_ID": score_job_id,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPYCACHEPREFIX": "/tmp/pycache",
    }


def poll_simple_bot_result(
    user_identifier: str, timeout_sec: int, result_url: str
) -> bool | None:
    deadline = time.time() + timeout_sec
    max_attempts = config.challenge.simple_bot_poll_max_attempts
    interval_sec = config.challenge.simple_bot_poll_interval_sec

    for attempt in range(max_attempts):
        remaining_sec = deadline - time.time()
        if remaining_sec <= 0:
            break
        response = requests.get(
            f"{result_url}/api/bot-status",
            params={"user_identifier": user_identifier},
            timeout=min(10, remaining_sec),
        )
        response.raise_for_status()
        data = response.json()
        if data.get("isBot") is not None:
            return data.get("isBot")
        if attempt + 1 < max_attempts:
            time.sleep(min(interval_sec, max(0, deadline - time.time())))
    return None

# -*- coding: utf-8 -*-

import os
import pathlib
import time
import docker
from typing import Dict, Optional

import requests
from pydantic import validate_call
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from api.core import utils
from api.config import config
from api.logger import logger

from .schemas import Fingerprinter



_BOT_DIR = str(pathlib.Path(__file__).resolve().parents[3] / "bot")
_BOT_DOCKERFILE_PATH = os.path.join(_BOT_DIR, "Dockerfile")
_BOT_PY_PATH = os.path.join(_BOT_DIR, "src", "core", "bot.py")



@validate_call(config={"arbitrary_types_allowed": True})
def ensure_bot_network(docker_client: docker.DockerClient) -> str:
    """
    Ensure isolated network for bot execution exists.
    The network is persistent and shared with the challenge container.
    Does NOT remove/recreate to avoid disrupting the challenge container connection.

    Args:
        docker_client: Docker client instance

    Returns:
        Network name
    """
    network_name = "bot-executor-net"

    # Check if network already exists
    try:
        existing_network = docker_client.networks.get(network_name)
        logger.info(f"Bot network '{network_name}' already exists, using existing network")
        return network_name
    except docker.errors.NotFound:
        logger.info(f"Bot network '{network_name}' not found, creating it...")

    # Create internal network (no internet access, only internal communication)
    try:
        docker_client.networks.create(
            name=network_name,
            driver="bridge",
            internal=True,  # No external/internet access
            check_duplicate=True,
            labels={"type": "bot-executor"}
        )
        logger.success(f"Isolated bot network '{network_name}' created successfully")
    except docker.errors.APIError as e:
        # Network might have been created by another process (race condition)
        if "already exists" in str(e).lower():
            logger.info(f"Bot network '{network_name}' already exists (created concurrently)")
        else:
            raise

    return network_name


@validate_call(config={"arbitrary_types_allowed": True})
def cleanup_bot_network(docker_client: docker.DockerClient, network_name: str) -> None:
    """
    Clean up the isolated bot network after execution.

    Args:
        docker_client: Docker client instance
        network_name: Name of the network to cleanup
    """
    try:
        network = docker_client.networks.get(network_name)
        network.remove()
        logger.info(f"Cleaned up bot network: {network_name}")
    except docker.errors.NotFound:
        logger.warning(f"Bot network '{network_name}' not found for cleanup")
    except Exception as e:
        logger.warning(f"Failed to cleanup bot network '{network_name}': {e}")


@validate_call
def build_and_run_bot(bot_py: str, dockerfile: str, session_count: int) -> Dict:
    """
    Build and run bot container with provided bot.py and Dockerfile.

    Args:
        bot_py: Bot Python source code
        dockerfile: Dockerfile content (without ENTRYPOINT, will be added)
        session_count: Number of sessions to run

    Returns:
        Dict containing execution results
    """
    logger.info("Starting build_and_run_bot process...")

    # Save bot.py to the correct location
    logger.info(f"Saving bot.py to {_BOT_PY_PATH}")
    with open(_BOT_PY_PATH, "w") as f:
        f.write(bot_py)

    # Process dockerfile: remove any existing ENTRYPOINT and add our own with script copy
    dockerfile_lines = dockerfile.strip().split("\n")
    filtered_lines = [line for line in dockerfile_lines if not line.strip().startswith("ENTRYPOINT")]

    # Add COPY for entrypoint script and set it as ENTRYPOINT
    final_dockerfile = "\n".join(filtered_lines) + "\n"
    # Use relative path from build context (bot directory)
    final_dockerfile += "COPY ./scripts/docker-entrypoint.sh /docker-entrypoint.sh\n"
    final_dockerfile += "RUN sudo chmod +x /docker-entrypoint.sh && sudo chown seluser:seluser /docker-entrypoint.sh\n"
    final_dockerfile += 'ENTRYPOINT ["/docker-entrypoint.sh"]\n'

    # Save Dockerfile
    logger.info(f"Saving Dockerfile to {_BOT_DOCKERFILE_PATH}")
    with open(_BOT_DOCKERFILE_PATH, "w") as f:
        f.write(final_dockerfile)

    # Build Docker image
    logger.info("Building Docker image...")
    docker_client = docker.from_env()

    image_tag = f"hbc-bot:latest-{int(time.time())}"
    bot_network_name = None

    try:
        image, build_logs = docker_client.images.build(
            path=_BOT_DIR,
            tag=image_tag,
            rm=True,
            forcerm=True,
        )

        for log in build_logs:
            if 'stream' in log:
                logger.debug(f"Build: {log['stream'].strip()}")

        logger.success(f"Successfully built image: {image_tag}")

        # Ensure bot network exists (shared with challenge container)
        bot_network_name = ensure_bot_network(docker_client)

        # Run the container with read-only volume mount and security restrictions
        logger.info(f"Running container for {session_count} sessions...")

        # Get challenge VM endpoint from config
        # Use container name as hostname since both containers are on bot-executor-net
        challenge_vm_host = os.getenv("CHALLENGE_VM_HOST", "challenger-api")
        challenge_vm_port = os.getenv("CHALLENGE_VM_PORT", "10001")
        web_url = f"http://{challenge_vm_host}:{challenge_vm_port}/_web"

        logger.info(f"Bot will connect to: {web_url}")

        # chek if bot_container exists and remove it
        try:
            existing_container = docker_client.containers.get("bot_container")
            logger.info("Removing existing bot_container...")
            existing_container.remove(force=True)
        except docker.errors.NotFound:
            pass

        container = docker_client.containers.run(
            image_tag,
            name="bot_container",
            environment={
                "HBC_WEB_URL": web_url,
                "HBC_SESSION_COUNT": 3,
            },
            network=bot_network_name,  # Use isolated bot network (no internet access)
            tmpfs={
                "/tmp": "size=512M,mode=1777",  # Writable /tmp for Chrome
                "/dev/shm": "size=2g",  # Shared memory for Chrome (prevents crashes)
            },
            mem_limit="8g",  # Memory limit - Chrome needs more memory
            memswap_limit="8g",  # Disable swap
            cpu_quota=100000,  # 50% CPU limit (50000 = 50%)
            pids_limit=256,  # Limit number of processes - Chrome spawns multiple processes
            cap_drop=["NET_RAW", "NET_ADMIN"],  # Drop dangerous capabilities only
            security_opt=["no-new-privileges"],  # Prevent privilege escalation
            remove=True,
            detach=False,
            shm_size="4g",  # Shared memory size for Chrome
            # read_only=True,  # Read-only root filesystem - disabled for Chrome compatibility
        )

        logger.success("Bot execution completed successfully")

        # Cleanup: remove the image
        try:
            docker_client.images.remove(image_tag, force=True)
            logger.info(f"Cleaned up image: {image_tag}")
        except Exception as e:
            logger.warning(f"Failed to cleanup image: {e}")

        # Note: Network is NOT cleaned up as it's persistent and shared with challenge container

        return {
            "status": "success",
            "message": "Bot executed successfully",
            "sessions_completed": session_count,
        }

    except docker.errors.BuildError as e:
        logger.error(f"Docker build error: {e}")
        raise ValueError(f"Failed to build Docker image: {str(e)}")
    except docker.errors.ContainerError as e:
        logger.error(f"Container execution error: {e}")
        raise ValueError(f"Container execution failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


__all__ = [
    "ensure_bot_network",
    "cleanup_bot_network",
    "build_and_run_bot",
]

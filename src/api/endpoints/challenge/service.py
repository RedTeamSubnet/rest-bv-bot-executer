# -*- coding: utf-8 -*-

import os
import pathlib
import time
import docker
from typing import Dict

import requests
from pydantic import validate_call
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from api.core import utils
from api.config import config
from api.logger import logger

from .schemas import Fingerprinter


_API_DIR = str(pathlib.Path(__file__).resolve().parents[2])
_BOT_DIR = str(pathlib.Path(__file__).resolve().parents[3] / "bot")
_BOT_DOCKERFILE_PATH = os.path.join(_BOT_DIR, "Dockerfile")
_BOT_PY_PATH = os.path.join(_BOT_DIR, "src", "core", "bot.py")


@validate_call
def save_fingerprinter(fingerprinter: Fingerprinter) -> None:

    _fp_js_path = os.path.join(_API_DIR, "static", "js", "fingerprinter.js")
    utils.remove_file(_fp_js_path)

    with open(_fp_js_path, "w") as _file:
        _file.write(fingerprinter.fingerprinter_js)

    return


@validate_call(config={"arbitrary_types_allowed": True})
def get_web(request: Request) -> HTMLResponse:

    _templates = Jinja2Templates(directory=os.path.join(_API_DIR, "templates", "html"))
    _html_response: HTMLResponse = _templates.TemplateResponse(
        request=request,
        name="index.html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
    return _html_response


@validate_call
def submit_fingerprint(order_id: int, fingerprint: str) -> None:

    _endpoint = "/_fingerprint"
    _base_url = str(config.challenge.base_url).rstrip("/")

    _url = f"{_base_url}{_endpoint}"
    _headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-API-Key": config.challenge.api_key.get_secret_value(),
    }
    _payload = {"order_id": order_id, "fingerprint": fingerprint}
    _response = requests.post(_url, headers=_headers, json=_payload)
    _response.raise_for_status()

    return


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

        # Run the container with read-only volume mount and security restrictions
        logger.info(f"Running container for {session_count} sessions...")

        # Get challenge VM endpoint from config
        challenge_vm_host = os.getenv("CHALLENGE_VM_HOST", "humanize-behaviour-net")
        challenge_vm_port = os.getenv("CHALLENGE_VM_PORT", "10002")
        web_url = f"http://{challenge_vm_host}:{challenge_vm_port}/_web"

        container = docker_client.containers.run(
            image_tag,
            environment={
                "HBC_WEB_URL": web_url,
                "HBC_SESSION_COUNT": str(session_count),
            },
            network="humanize-behaviour-net",  # Use shared network for service access
            tmpfs={"/tmp": "size=100M,mode=1777"},  # Writable /tmp with size limit
            mem_limit="512m",  # Memory limit
            memswap_limit="512m",  # Disable swap
            cpu_quota=50000,  # 50% CPU limit (100000 = 100%)
            pids_limit=100,  # Limit number of processes
            cap_drop=["ALL"],  # Drop all capabilities
            cap_add=["NET_BIND_SERVICE"],  # Only allow network binding
            security_opt=["no-new-privileges"],  # Prevent privilege escalation
            remove=True,
            detach=False,
            # read_only=True,  # Read-only root filesystem
        )

        logger.success("Bot execution completed successfully")

        # Cleanup: remove the image
        try:
            docker_client.images.remove(image_tag, force=True)
            logger.info(f"Cleaned up image: {image_tag}")
        except Exception as e:
            logger.warning(f"Failed to cleanup image: {e}")

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
    "save_fingerprinter",
    "get_web",
    "submit_fingerprint",
    "build_and_run_bot",
]

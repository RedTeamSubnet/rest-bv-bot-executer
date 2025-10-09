#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Standard libraries
import os
import sys
import json
import logging
import subprocess

## Internal modules
from constants import ENV_PREFIX
from driver import WebUIAutomate


logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S %z",
        format="[%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d]: %(message)s",
    )

    logger.info("Starting WebUI automation bot...")

    # Get web URL from environment variable
    _web_url = os.getenv(f"{ENV_PREFIX}WEB_URL")
    if not _web_url:
        # Fallback: try to get host gateway IP
        _command = "ip route | awk '/default/ { print $3 }'"
        try:
            _host = subprocess.check_output(_command, shell=True, text=True).strip()
        except Exception:
            _host = "humanize-behaviour-net"  # Docker Desktop default
        _web_url = f"http://{_host}:10002/_web"
        logger.warning(f"HBC_WEB_URL not set, using fallback: {_web_url}")

    logger.info(f"Challenge web URL: {_web_url}")

    _session_count = os.getenv(f"{ENV_PREFIX}SESSION_COUNT")
    for _ in range(int(_session_count) if _session_count else 2):
        _webui_automate = WebUIAutomate(web_url=_web_url)
        _webui_automate()

    logger.info("Done!\n")
    return


if __name__ == "__main__":
    main()

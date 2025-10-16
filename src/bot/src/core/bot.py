import logging
import time
import json
from typing import Any, Dict, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import requests

logger = logging.getLogger(__name__)


def test_network_connectivity(driver: WebDriver, web_endpoint: Optional[str] = None) -> Dict[str, Any]:
    """Test network connectivity using both direct requests and host network via _web endpoint.

    Args:
        driver: Selenium WebDriver instance for executing JavaScript
        web_endpoint: Optional URL to the _web endpoint (e.g., https://172.17.0.1:10001/_web)

    Returns:
        Dict containing test results and logs
    """
    results = {
        "direct_test": {},
        "host_network_test": {},
        "timestamp": time.time()
    }

    if web_endpoint:
        logger.info("\n[TEST 2] Testing access to google.com via host network (_web endpoint)")
        logger.info(f"Using _web endpoint: {web_endpoint}")
        logger.info("-" * 80)

        try:
            logger.info("Injecting JavaScript to fetch google.com from host network...")
            # Use the browser's fetch API which will use the host network
            fetch_script = """
            return new Promise((resolve, reject) => {
                fetch('https://www.google.com', {
                    method: 'GET',
                    mode: 'cors',
                    credentials: 'omit'
                })
                .then(response => {
                    console.log('Fetch response received:', response.status);
                    return response.text().then(text => ({
                        status: response.status,
                        statusText: response.statusText,
                        headers: Object.fromEntries(response.headers.entries()),
                        text: text,
                        ok: response.ok
                    }));
                })
                .then(data => {
                    console.log('Response data parsed, length:', data.text.length);
                    resolve(data);
                })
                .catch(error => {
                    console.error('Fetch error:', error);
                    reject(error.toString());
                });
            });
            """

            logger.info("Executing fetch request via browser...")
            start_time = time.time()
            fetch_result = driver.execute_async_script(fetch_script)
            elapsed = time.time() - start_time

            if fetch_result and isinstance(fetch_result, dict):
                logger.info(f"✓ Host network request SUCCESSFUL")
                logger.info(f"  - Status Code: {fetch_result.get('status')}")
                logger.info(f"  - Status Text: {fetch_result.get('statusText')}")
                logger.info(f"  - Response Time: {elapsed:.2f}s")
                logger.info(f"  - Content Length: {len(fetch_result.get('text', ''))} bytes")
                logger.info(f"  - Headers: {fetch_result.get('headers')}")
                logger.info(f"\n  - Response HTML (first 500 chars):\n{fetch_result.get('text', '')[:500]}")
                logger.info(f"\n  - Response HTML (last 500 chars):\n{fetch_result.get('text', '')[-500:]}")

                results["host_network_test"] = {
                    "success": True,
                    "status_code": fetch_result.get('status'),
                    "status_text": fetch_result.get('statusText'),
                    "response_time": elapsed,
                    "content_length": len(fetch_result.get('text', '')),
                    "headers": fetch_result.get('headers'),
                    "html_preview": fetch_result.get('text', '')[:1000]
                }
            else:
                logger.error(f"✗ Host network request returned unexpected result: {fetch_result}")
                results["host_network_test"] = {
                    "success": False,
                    "error": "unexpected_result",
                    "message": str(fetch_result)
                }

        except Exception as e:
            logger.error(f"✗ Host network request FAILED: {e}")
            logger.error(f"  - Error Type: {type(e).__name__}")
            logger.error(f"  - Error Details: {str(e)}")
            results["host_network_test"] = {
                "success": False,
                "error": type(e).__name__,
                "message": str(e)
            }

            # Try to get browser console logs for more details
            try:
                console_logs = driver.get_log("browser")
                if console_logs:
                    logger.info("Browser console logs during host network test:")
                    for entry in console_logs:
                        logger.info(f"  [{entry.get('level')}] {entry.get('message')}")
            except Exception as log_error:
                logger.warning(f"Could not retrieve console logs: {log_error}")
    else:
        logger.warning("\n[TEST 2] Skipped - No _web endpoint provided")
        results["host_network_test"] = {"success": False, "error": "no_endpoint", "message": "No _web endpoint provided"}

    logger.info("\n" + "=" * 80)
    logger.info("NETWORK CONNECTIVITY TESTS COMPLETED")
    logger.info("=" * 80)
    logger.info(f"Summary:")
    logger.info(f"  - Direct Test: {'✓ PASSED' if results['direct_test'].get('success') else '✗ FAILED'}")
    logger.info(f"  - Host Network Test: {'✓ PASSED' if results['host_network_test'].get('success') else '✗ FAILED'}")
    logger.info("=" * 80 + "\n")

    return results


def run_bot(
    driver: WebDriver,
) -> bool:
    """Run bot to automate login.

    Args:
        driver   (WebDriver, required): Selenium WebDriver instance.
        web_endpoint (str, optional): URL to the _web endpoint for host network access.

    Returns:
        bool: True if login is successful, False otherwise.
    """

    try:
        _wait = WebDriverWait(driver, 15)

        mouse = PointerInput(kind="mouse", name="mouse")

        # Run comprehensive network connectivity tests
        logger.info("\n" + "=" * 80)
        logger.info("INITIATING COMPREHENSIVE NETWORK CONNECTIVITY TESTS")
        logger.info("=" * 80 + "\n")
        web_endpoint = "https://google.com"

        network_test_results = test_network_connectivity(driver, web_endpoint)

        logger.info("\n" + "=" * 80)
        logger.info("NETWORK TEST RESULTS SUMMARY")
        logger.info("=" * 80)
        logger.info(json.dumps(network_test_results, indent=2, default=str))
        logger.info("=" * 80 + "\n")

        # Execute JavaScript to get ACTIONS_LIST
        actions_list = json.loads(driver.execute_script("return window.ACTIONS_LIST;"))
        if actions_list:
            logger.info("Retrieved config from window.ACTIONS_LIST")
        else:
            logger.error("window.ACTIONS_LIST is empty or doesn't exist")
            return False

        # Handle nested list structure - if actions_list is a list of lists, flatten it
        if isinstance(actions_list, list) and len(actions_list) > 0 and isinstance(actions_list[0], list):
            logger.info("Detected nested actions_list structure, flattening...")
            actions_list = actions_list[0]

        # Perform configured actions
        for i, _action in enumerate(actions_list):
            if _action["type"] == "click":
                x = _action["args"]["location"]["x"]
                y = _action["args"]["location"]["y"]

                logger.info(f"Action {i+1}: Clicking at ({x}, {y})")

                try:
                    actions = ActionBuilder(driver, mouse=mouse)
                    actions.pointer_action.move_to_location(x, y)
                    actions.pointer_action.click()
                    actions.perform()

                    time.sleep(0.5)

                except Exception as e:
                    logger.error(f"Failed to perform action {i+1}: {e}")
                    continue

            if _action["type"] == "input":
                _selector = _action["selector"]
                _args = _action["args"]

                logger.info(
                    f"Action {i+1}: Inputting '{_args['text']}' to '{_selector}'"
                )

                try:
                    _element = driver.find_element(By.ID, _selector["id"])
                    _element.clear()
                    _element.send_keys(_args["text"])
                except Exception as e:
                    logger.error(f"Failed to perform action {i+1}: {e}")
                    continue

        # Click login button without scrolling
        _login_button = _wait.until(
            EC.presence_of_element_located((By.ID, "login-button"))
        )
        _login_button.click()

        logger.info("Scrolling to find end-session button")

        lenOfPage = driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;"
        )
        logger.info(f"Initial page length: {lenOfPage}")
        match = False
        while match == False:
            lastCount = lenOfPage
            time.sleep(3)
            lenOfPage = driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;"
            )
            if lastCount == lenOfPage:
                logger.info("Reached bottom of page")
                match = True

        _end_session_button = _wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "end-session"))
        )

        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            _end_session_button,
        )
        time.sleep(1)  # Give time for smooth scrolling to complete

        _end_session_button.click()
        logger.info("Clicked end-session button")

        # Give the browser a moment to flush console messages
        time.sleep(1)

        # Attempt to read browser console logs (may not be supported by all drivers)
        try:
            console_logs = driver.get_log("browser")
            if console_logs:
                logger.info("Browser console logs:")
                for entry in console_logs:
                    # Typical entry keys: level, message, source, timestamp
                    level = entry.get("level")
                    msg = entry.get("message")
                    source = entry.get("source") or entry.get("sourceURL") or ""
                    ts = entry.get("timestamp")
                    logger.info(f"[console][{level}] {ts} {source} - {msg}")
            else:
                logger.info("No browser console logs available.")
        except Exception as e:
            logger.warning(f"Could not retrieve browser console logs: {e}")

        return True

    except Exception as err:
        logger.error(f"Login failed: {err}")
        return False

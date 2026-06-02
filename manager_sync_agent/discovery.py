import requests
from tax_capsule.utils.logger import get_logger

logger = get_logger("ManagerioDiscovery")


def discover_managerio(base_url: str) -> dict:
    try:
        response = requests.get(base_url, timeout=5)
        logger.info(f"Manager.io reachable at {base_url}: HTTP {response.status_code}")
        return {"status": "reachable", "code": response.status_code, "url": base_url}
    except requests.exceptions.ConnectionError:
        logger.warning(f"Manager.io not reachable at {base_url}")
        return {"status": "unreachable", "url": base_url}
    except requests.exceptions.Timeout:
        logger.warning(f"Manager.io timed out at {base_url}")
        return {"status": "timeout", "url": base_url}
    except Exception as e:
        logger.error(f"Discovery error: {e}")
        return {"status": "error", "error": str(e), "url": base_url}

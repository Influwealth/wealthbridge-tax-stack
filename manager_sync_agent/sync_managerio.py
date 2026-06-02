import os
import requests
from tax_capsule.utils.logger import get_logger

logger = get_logger("ManagerioSync")

MANAGERIO_BASE_URL = os.getenv("MANAGERIO_BASE_URL", "https://api.manager.io")
MANAGERIO_API_KEY = os.getenv("MANAGERIO_API_KEY", "")


def _get_headers() -> dict:
    return {
        "Authorization": f"Bearer {MANAGERIO_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def pull_managerio_data(endpoint: str = "/api/general-ledger-transactions") -> dict:
    if not MANAGERIO_API_KEY:
        logger.warning("MANAGERIO_API_KEY not set — returning empty data")
        return {
            "data": [],
            "source": "managerio",
            "warning": "API key not configured",
        }

    url = f"{MANAGERIO_BASE_URL}{endpoint}"
    try:
        response = requests.get(url, headers=_get_headers(), timeout=10)
        response.raise_for_status()
        data = response.json()
        record_count = len(data) if isinstance(data, list) else 1
        logger.info(f"Pulled {record_count} records from Manager.io")
        return {"data": data, "source": "managerio", "record_count": record_count}
    except requests.exceptions.ConnectionError:
        logger.error(f"Could not connect to Manager.io at {url}")
        return {"data": [], "error": "Connection failed", "source": "managerio"}
    except requests.exceptions.Timeout:
        logger.error(f"Manager.io request timed out at {url}")
        return {"data": [], "error": "Request timed out", "source": "managerio"}
    except requests.exceptions.HTTPError as e:
        logger.error(f"Manager.io HTTP error: {e.response.status_code}")
        return {"data": [], "error": f"HTTP {e.response.status_code}", "source": "managerio"}
    except Exception as e:
        logger.error(f"Unexpected error pulling Manager.io data: {e}")
        return {"data": [], "error": "Unexpected error", "source": "managerio"}

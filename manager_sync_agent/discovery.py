import requests

def discover_managerio(base_url: str):
    try:
        r = requests.get(base_url, timeout=5)
        return {"status": "reachable", "code": r.status_code}
    except Exception as e:
        return {"status": "error", "error": str(e)}

import requests
import time
from lib.config import get_config

TIMEOUT = 10
MAX_RETRY = 3

def _get_url_headers(table):
    cfg = get_config()

    url = f"https://api.airtable.com/v0/{cfg['BASE_ID']}/{table}"
    headers = {
        "Authorization": f"Bearer {cfg['TOKEN']}",
        "Content-Type": "application/json"
    }

    return url, headers


def request(method, table, **kwargs):
    url, headers = _get_url_headers(table)

    for attempt in range(MAX_RETRY):
        try:
            res = requests.request(method, url, headers=headers, timeout=TIMEOUT, **kwargs)

            if res.status_code in [200, 201]:
                return res.json()

            if res.status_code >= 500:
                time.sleep(1 * (attempt + 1))
                continue

            print("Airtable Error:", res.status_code, res.text)
            return None

        except Exception as e:
            print("Request Error:", str(e))
            time.sleep(1 * (attempt + 1))

    return None
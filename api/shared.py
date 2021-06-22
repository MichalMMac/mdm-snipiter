import json
import logging
import time

import requests


class APIException(Exception):
    pass


def contact_api(
    url, headers, payload=None, operation="GET", attempts=3, notfound404=False
):
    """Send HTTP request to Snipe-IT API. Reattempt if request fails."""

    for i in range(1, attempts):

        try:
            if operation == "PATCH":
                response = requests.patch(url, json=payload, headers=headers)
            elif operation == "POST":
                response = requests.post(url, json=payload, headers=headers)
            elif operation == "GET":
                response = requests.get(url, headers=headers)
            if str(response.status_code).startswith("2"):
                return response.json()
            if notfound404 and response.status_code == 404:
                return None

        except (requests.ConnectionError, json.JSONDecodeError) as ex:
            logging.error("Exception occured during API request")
            logging.error(ex)

        sleeptimer = 1 * (1.8 ** (i - 1))
        logging.info(f"Sleeping for: {sleeptimer}s")
        time.sleep(sleeptimer)

    raise APIException("Unable to get valid response from API")

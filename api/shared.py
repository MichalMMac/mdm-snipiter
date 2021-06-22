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


def load_configuration(filepath, options_template):
    """Load configuration from JSON config file"""

    preferences = {}
    try:
        with open(filepath) as jfile:
            config = json.load(jfile)

            for option in options_template:
                o_key = option["key"]
                preferences[o_key] = config.get(o_key)
                if not preferences[o_key]:
                    if option.get("default"):
                        preferences[o_key] = option.get("default")
                    else:
                        raise Exception(f"Configuration file is missing '{o_key}'")

    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file '{filepath}' is missing")
    except Exception:
        raise Exception(f"Error reading '{filepath}' configuration file")

    return preferences

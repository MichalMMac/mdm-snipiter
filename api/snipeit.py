import json
import logging
import os
import sys
import time

import requests

from .shared import APIException, contact_api

class SnipeITAPIException(Exception):
    pass


# Configure SnipeIT API module
try:
    with open(os.path.join(sys.path[0], "api", "snipeit.conf")) as jfile:
        config = json.load(jfile)

        log_level = config.get("log_level")
        if not log_level:
            log_level = "WARNING"

        log_path = config.get("log_path")
        if not log_path:
            log_path = "/var/log/mdmsnipiter/snipeit.log"

        snipeit_url = config.get("url")
        if not snipeit_url:
            raise SnipeITAPIException("Configuration file is missing 'url'")

        token = config.get("token")
        if not token:
            raise SnipeITAPIException("Configuration file is missing 'token'")

        attempts = config.get("attempts", 5)

except SnipeITAPIException:
    raise
except FileNotFoundError:
    raise SnipeITAPIException("Configuration file 'snipeit.conf' is missing")
except Exception:
    raise SnipeITAPIException("Error reading 'snipeit.conf' configuration file")


api_endpoint = f"{snipeit_url}/api/v1"
headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
logging.basicConfig(filename=log_path, level=log_level)


def get_data_from_api(url):
    try:
        data = contact_api(url, headers)
    except APIException as ex:
        raise SnipeITAPIException(ex)
    rows = data.get("rows", None)

    if rows is None:
        raise SnipeITAPIException("Unexpected API response. Missing rows array")
    elif not rows:  # Correct response but no assent found
        return None

    return rows

def find_asset(serial):
    """Try to find Snipe-IT asset by its serial number"""

    logging.info(f"Searching for asset with serial number: {serial}")

    rows = get_data_from_api(f"{api_endpoint}/hardware/byserial/{serial}")

    if rows:
        if len(rows) > 1:
            raise SnipeITAPIException(
                "Unexpected API response. Multiple objects with same serial number."
            )
        else:
            return rows[0]

    return None


def checkout(asset_id, user_id, asset_name=None):
    """Assign user to the asset"""

    logging.info(f"Checking out asset: {asset_id} to user: {user_id}")

    url = f"{api_endpoint}/hardware/{asset_id}/checkout"
    payload = {"checkout_to_type": "user", "assigned_user": user_id}
    if asset_name:
        payload["name"] = asset_name

    try:
        response = contact_api(url, payload)
    except APIException as ex:
        raise SnipeITAPIException(ex)

    if response.get("status") == "error":
        messages = response.get("messages", "Unknown error")
        logging.error(f"API returner error response: {messages}")
        return False
    return True


def checkin(asset_id):
    """Unassign user from the asset"""

    logging.info(f"Checking in asset: {asset_id}")

    url = f"{api_endpoint}/hardware/{asset_id}/checkin"

    try:
        response = contact_api(url, type="POST")
    except APIException as ex:
        raise SnipeITAPIException(ex)

    if response.get("status") == "error":
        messages = response.get("messages", "Unknown error")
        logging.error(f"API returned error response: {messages}")
        return False
    return True
